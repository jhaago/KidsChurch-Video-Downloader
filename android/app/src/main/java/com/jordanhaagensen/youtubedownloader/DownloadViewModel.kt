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

enum class OutputFormat(
    val displayName: String,
    val shortName: String,
    val extension: String,
    val mimeType: String
) {
    MP4_VIDEO("MP4 Video", "MP4", "mp4", "video/mp4"),
    MP3_AUDIO("MP3 Audio", "MP3", "mp3", "audio/mpeg"),
    WAV_AUDIO("WAV Audio", "WAV", "wav", "audio/wav")
}

data class DownloadUiState(
    val url: String = "",
    val selectedFormat: OutputFormat = OutputFormat.MP4_VIDEO,
    val videoQuality: String = "1080p",
    val status: String = "Ready",
    val progress: Float = 0f,
    val etaSeconds: Long? = null,
    val isDownloading: Boolean = false,
    val savedFileName: String? = null,
    val engineVersion: String? = null,
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
    private var engineCheckedThisLaunch = false

    fun setUrl(value: String) {
        _state.value = _state.value.copy(url = value, error = null)
    }

    fun setOutputFormat(format: OutputFormat) {
        if (_state.value.isDownloading) return
        _state.value = _state.value.copy(
            selectedFormat = format,
            savedFileName = null,
            error = null
        )
    }

    fun setVideoQuality(quality: String) {
        if (_state.value.isDownloading) return
        if (quality !in VIDEO_QUALITIES) return
        _state.value = _state.value.copy(
            videoQuality = quality,
            savedFileName = null,
            error = null
        )
    }

    fun acceptSharedText(text: String?) {
        if (text.isNullOrBlank()) return
        val match = Regex("""https?://\S+""").find(text)?.value ?: text.trim()
        if (match.isNotBlank()) {
            setUrl(match)
        }
    }

    fun startDownload() {
        if (_state.value.isDownloading) return

        val snapshot = _state.value
        val url = snapshot.url.trim()
        val format = snapshot.selectedFormat
        val videoQuality = snapshot.videoQuality

        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            _state.value = snapshot.copy(error = "Paste a valid YouTube URL first.")
            return
        }

        if (!DownloaderRuntime.ready) {
            _state.value = snapshot.copy(
                error = DownloaderRuntime.error ?: "The download engine is not ready yet."
            )
            return
        }

        val id = "android-${format.extension}-${UUID.randomUUID()}"
        processId = id

        _state.value = snapshot.copy(
            isDownloading = true,
            progress = 0f,
            etaSeconds = null,
            status = "Preparing ${format.shortName} download…",
            savedFileName = null,
            error = null
        )

        job = viewModelScope.launch(Dispatchers.IO) {
            val context = getApplication<Application>()
            val sessionDir = File(context.cacheDir, "downloads/$id").apply { mkdirs() }

            try {
                _state.value = _state.value.copy(
                    status = "Checking yt-dlp for updates…",
                    progress = 0f
                )

                ensureCurrentYoutubeDL(context)

                val currentVersion = YoutubeDL.getInstance().version(context)
                _state.value = _state.value.copy(
                    engineVersion = currentVersion,
                    status = "Preparing ${format.shortName} download…"
                )

                val request = buildRequest(
                    url = url,
                    format = format,
                    videoQuality = videoQuality,
                    sessionDir = sessionDir
                )

                YoutubeDL.getInstance().execute(request, id) { progress, eta, _ ->
                    _state.value = _state.value.copy(
                        progress = progress.coerceIn(0f, 100f),
                        etaSeconds = eta.takeIf { it >= 0 },
                        status = "Downloading ${format.shortName}…"
                    )
                }

                val outputFile = findOutputFile(sessionDir, format)
                val publishedName = publishToDownloads(
                    context = context,
                    source = outputFile,
                    mimeType = format.mimeType
                )

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
                    ?.take(300)
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

    private fun buildRequest(
        url: String,
        format: OutputFormat,
        videoQuality: String,
        sessionDir: File
    ): YoutubeDLRequest {
        return YoutubeDLRequest(url).apply {
            addOption("--no-playlist")
            addOption("--no-mtime")
            addOption("--remote-components", "ejs:github")
            addOption(
                "-o",
                File(sessionDir, "%(title).180B.%(ext)s").absolutePath
            )

            when (format) {
                OutputFormat.MP3_AUDIO -> {
                    addOption("--extract-audio")
                    addOption("--audio-format", "mp3")
                    addOption("--audio-quality", "320K")
                }

                OutputFormat.WAV_AUDIO -> {
                    addOption("--extract-audio")
                    addOption("--audio-format", "wav")
                }

                OutputFormat.MP4_VIDEO -> {
                    val height = videoQuality.removeSuffix("p").toIntOrNull() ?: 1080
                    val selector =
                        "bestvideo[vcodec^=avc1][height<=$height]+" +
                            "bestaudio[acodec^=mp4a]/" +
                            "best[vcodec^=avc1][acodec^=mp4a][height<=$height]"
                    addOption("--format", selector)
                    addOption("--merge-output-format", "mp4")
                }
            }
        }
    }

    private fun findOutputFile(sessionDir: File, format: OutputFormat): File {
        return sessionDir
            .walkTopDown()
            .filter {
                it.isFile &&
                    it.extension.equals(format.extension, ignoreCase = true)
            }
            .maxByOrNull { it.lastModified() }
            ?: error(
                "The download finished but no ${format.shortName} file was produced."
            )
    }

    private fun ensureCurrentYoutubeDL(context: Context) {
        if (engineCheckedThisLaunch) return

        try {
            YoutubeDL.getInstance().updateYoutubeDL(
                context,
                YoutubeDL.UpdateChannel.STABLE
            )
            engineCheckedThisLaunch = true
        } catch (t: Throwable) {
            val installedVersion = YoutubeDL.getInstance().version(context)
            val suffix = if (installedVersion.isNullOrBlank()) {
                ""
            } else {
                " Installed version: $installedVersion."
            }
            throw IllegalStateException(
                "Could not update yt-dlp before downloading.$suffix " +
                    "Check your internet connection and try again.",
                t
            )
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

    private fun publishToDownloads(
        context: Context,
        source: File,
        mimeType: String
    ): String {
        val resolver = context.contentResolver
        val targetName = uniqueDisplayName(context, source.name)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, targetName)
                put(MediaStore.Downloads.MIME_TYPE, mimeType)
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
            val ext = requested.substringAfterLast(".", "bin")
            var index = 2
            while (File(targetDir, "$stem ($index).$ext").exists()) index++
            return "$stem ($index).$ext"
        }

        val stem = requested.substringBeforeLast(".")
        val ext = requested.substringAfterLast(".", "bin")
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

    companion object {
        val VIDEO_QUALITIES = listOf("1080p", "720p", "480p")
    }
}
