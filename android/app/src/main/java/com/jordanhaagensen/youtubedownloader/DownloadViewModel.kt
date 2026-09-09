package com.jordanhaagensen.youtubedownloader

import android.app.Application
import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileInputStream
import java.util.UUID

data class DownloadUiState(
    val url: String = "",
    val status: String = "Ready",
    val progress: Float = 0f,
    val etaSeconds: Long? = null,
    val isDownloading: Boolean = false,
    val savedFileName: String? = null,
    val error: String? = null
)

class DownloadViewModel(application: Application) : AndroidViewModel(application) {
    private val _state = MutableStateFlow(
        DownloadUiState(
            status = if (DownloaderRuntime.ready) {
                "Ready"
            } else {
                "Initialising download engine…"
            },
            error = DownloaderRuntime.error
        )
    )
    val state: StateFlow<DownloadUiState> = _state.asStateFlow()

    private var job: Job? = null
    private var processId: String? = null

    fun setUrl(value: String) {
        _state.value = _state.value.copy(url = value, error = null)
    }

    fun acceptSharedText(text: String?) {
        if (text.isNullOrBlank()) return
        val match = Regex("""https?://\S+""").find(text)?.value ?: text.trim()
        if (match.isNotBlank()) {
            setUrl(match)
        }
    }

    fun startMp3Download() {
        if (_state.value.isDownloading) return

        val url = _state.value.url.trim()
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            _state.value = _state.value.copy(error = "Paste a valid YouTube URL first.")
            return
        }

        if (!DownloaderRuntime.ready) {
            _state.value = _state.value.copy(
                error = DownloaderRuntime.error ?: "The download engine is not ready yet."
            )
            return
        }

        val id = "android-mp3-${UUID.randomUUID()}"
        processId = id

        _state.value = _state.value.copy(
            isDownloading = true,
            progress = 0f,
            etaSeconds = null,
            status = "Preparing download…",
            savedFileName = null,
            error = null
        )

        job = viewModelScope.launch(Dispatchers.IO) {
            val context = getApplication<Application>()
            val sessionDir = File(context.cacheDir, "downloads/$id").apply { mkdirs() }

            try {
                val request = YoutubeDLRequest(url).apply {
                    addOption("--no-playlist")
                    addOption("--no-mtime")
                    addOption("--extract-audio")
                    addOption("--audio-format", "mp3")
                    addOption("--audio-quality", "320K")
                    addOption("--remote-components", "ejs:github")
                    addOption(
                        "-o",
                        File(sessionDir, "%(title).180B.%(ext)s").absolutePath
                    )
                }

                YoutubeDL.getInstance().execute(request, id) { progress, eta, line ->
                    _state.value = _state.value.copy(
                        progress = progress.coerceIn(0f, 100f),
                        etaSeconds = eta.takeIf { it >= 0 },
                        status = if (line.isBlank()) "Downloading…" else line
                    )
                }

                val mp3 = sessionDir
                    .walkTopDown()
                    .filter { it.isFile && it.extension.equals("mp3", ignoreCase = true) }
                    .maxByOrNull { it.lastModified() }
                    ?: error("The download finished but no MP3 file was produced.")

                val publishedName = publishToDownloads(context, mp3)

                _state.value = _state.value.copy(
                    isDownloading = false,
                    progress = 100f,
                    etaSeconds = null,
                    status = "Download complete",
                    savedFileName = publishedName,
                    error = null
                )
            } catch (cancelled: CancellationException) {
                _state.value = _state.value.copy(
                    isDownloading = false,
                    status = "Cancelled",
                    etaSeconds = null
                )
                throw cancelled
            } catch (t: Throwable) {
                val message = t.message
                    ?.lineSequence()
                    ?.lastOrNull { it.isNotBlank() }
                    ?.take(240)
                    ?: t.javaClass.simpleName

                _state.value = _state.value.copy(
                    isDownloading = false,
                    etaSeconds = null,
                    status = "Download failed",
                    error = message
                )
            } finally {
                processId = null
                sessionDir.deleteRecursively()
            }
        }
    }

    fun cancelDownload() {
        val id = processId ?: return
        _state.value = _state.value.copy(status = "Cancelling…")

        runCatching {
            YoutubeDL.getInstance().destroyProcessById(id)
        }

        job?.cancel()
    }

    private fun publishToDownloads(context: Context, source: File): String {
        val resolver = context.contentResolver
        val targetName = uniqueDisplayName(context, source.name)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, targetName)
                put(MediaStore.Downloads.MIME_TYPE, "audio/mpeg")
                put(
                    MediaStore.Downloads.RELATIVE_PATH,
                    Environment.DIRECTORY_DOWNLOADS + "/YouTube Downloader"
                )
                put(MediaStore.Downloads.IS_PENDING, 1)
            }

            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: error("Android could not create the file in Downloads.")

            try {
                resolver.openOutputStream(uri, "w").use { output ->
                    requireNotNull(output) { "Android could not open the output file." }
                    FileInputStream(source).use { input ->
                        input.copyTo(output)
                    }
                }

                val completed = ContentValues().apply {
                    put(MediaStore.Downloads.IS_PENDING, 0)
                }
                resolver.update(uri, completed, null, null)
            } catch (t: Throwable) {
                resolver.delete(uri, null, null)
                throw t
            }
        } else {
            @Suppress("DEPRECATION")
            val downloads = Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS
            )
            val targetDir = File(downloads, "YouTube Downloader").apply { mkdirs() }
            source.copyTo(File(targetDir, targetName), overwrite = false)
        }

        return targetName
    }

    private fun uniqueDisplayName(context: Context, requested: String): String {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            @Suppress("DEPRECATION")
            val downloads = Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS
            )
            val targetDir = File(downloads, "YouTube Downloader")
            if (!File(targetDir, requested).exists()) return requested

            val stem = requested.substringBeforeLast(".")
            val ext = requested.substringAfterLast(".", "mp3")
            var index = 2
            while (File(targetDir, "$stem ($index).$ext").exists()) index++
            return "$stem ($index).$ext"
        }

        val stem = requested.substringBeforeLast(".")
        val ext = requested.substringAfterLast(".", "mp3")
        var candidate = requested
        var index = 2

        while (downloadNameExists(context, candidate)) {
            candidate = "$stem ($index).$ext"
            index++
        }
        return candidate
    }

    private fun downloadNameExists(context: Context, displayName: String): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return false

        val projection = arrayOf(MediaStore.Downloads._ID)
        val selection =
            "${MediaStore.Downloads.DISPLAY_NAME}=? AND ${MediaStore.Downloads.RELATIVE_PATH}=?"
        val args = arrayOf(
            displayName,
            Environment.DIRECTORY_DOWNLOADS + "/YouTube Downloader/"
        )

        context.contentResolver.query(
            MediaStore.Downloads.EXTERNAL_CONTENT_URI,
            projection,
            selection,
            args,
            null
        ).use { cursor ->
            return cursor?.moveToFirst() == true
        }
    }
}
