package com.jordanhaagensen.youtubedownloader

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle

class MainActivity : ComponentActivity() {
    private val viewModel: DownloadViewModel by viewModels()

    private val storagePermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                viewModel.startDownload()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        consumeShareIntent(intent)

        setContent {
            YouTubeDownloaderTheme {
                DownloaderScreen(
                    viewModel = viewModel,
                    onDownload = { startDownloadWithPermissionCheck() }
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        consumeShareIntent(intent)
    }

    private fun consumeShareIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            viewModel.acceptSharedText(intent.getStringExtra(Intent.EXTRA_TEXT))
        }
    }

    private fun startDownloadWithPermissionCheck() {
        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P &&
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.WRITE_EXTERNAL_STORAGE
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            storagePermissionLauncher.launch(Manifest.permission.WRITE_EXTERNAL_STORAGE)
            return
        }

        viewModel.startDownload()
    }
}

private val AppColors = darkColorScheme(
    primary = Color(0xFFFF5B64),
    onPrimary = Color.White,
    secondary = Color(0xFF77A7FF),
    background = Color(0xFF0F1115),
    surface = Color(0xFF171A21),
    surfaceVariant = Color(0xFF1D212A),
    onBackground = Color(0xFFF5F7FA),
    onSurface = Color(0xFFF5F7FA),
    outline = Color(0xFF39414F),
    error = Color(0xFFFF7D86)
)

@Composable
private fun YouTubeDownloaderTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AppColors,
        content = content
    )
}

@Composable
private fun DownloaderScreen(
    viewModel: DownloadViewModel,
    onDownload: () -> Unit
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val muted = Color(0xFF9BA5B3)
    val card = Color(0xFF171A21)
    val accent = MaterialTheme.colorScheme.primary
    val scroll = rememberScrollState()

    val qualityText = when (state.selectedFormat) {
        OutputFormat.MP4_VIDEO -> state.videoQuality
        OutputFormat.MP3_AUDIO -> "320 kbps • high quality"
        OutputFormat.WAV_AUDIO -> "Uncompressed PCM"
    }

    val downloadButtonText = when (state.selectedFormat) {
        OutputFormat.MP4_VIDEO -> "Download MP4 • ${state.videoQuality}"
        OutputFormat.MP3_AUDIO -> "Download MP3 • 320 kbps"
        OutputFormat.WAV_AUDIO -> "Download WAV • PCM"
    }

    val statusBadge = when {
        state.isDownloading -> "DOWNLOADING"
        state.error != null -> "FAILED"
        state.savedFileName != null -> "COMPLETE"
        else -> "READY"
    }

    val statusBadgeColor = when (statusBadge) {
        "DOWNLOADING" -> Color(0xFF77A7FF)
        "FAILED" -> MaterialTheme.colorScheme.error
        "COMPLETE" -> Color(0xFF55C989)
        else -> muted
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .verticalScroll(scroll)
                .padding(horizontal = 20.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Column {
                Text(
                    text = "ANDROID • V0.2",
                    color = accent,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(3.dp))
                Text(
                    text = "YouTube Downloader",
                    color = MaterialTheme.colorScheme.onBackground,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    text = "Download video or audio directly to your phone.",
                    color = muted,
                    fontSize = 14.sp
                )
            }

            Card(
                colors = CardDefaults.cardColors(containerColor = card),
                shape = RoundedCornerShape(18.dp)
            ) {
                Column(
                    modifier = Modifier.padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Text(
                        text = "YouTube link",
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 16.sp
                    )

                    OutlinedTextField(
                        value = state.url,
                        onValueChange = viewModel::setUrl,
                        enabled = !state.isDownloading,
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("https://youtube.com/watch?v=…") },
                        singleLine = false,
                        minLines = 2,
                        shape = RoundedCornerShape(12.dp)
                    )

                    Text(
                        text = "Tip: in the YouTube app, tap Share → YouTube Downloader.",
                        color = muted,
                        fontSize = 13.sp
                    )

                    Text(
                        text = "Format",
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutputChoiceButton(
                            label = "MP4",
                            selected = state.selectedFormat == OutputFormat.MP4_VIDEO,
                            enabled = !state.isDownloading,
                            modifier = Modifier.weight(1f),
                            onClick = {
                                viewModel.setOutputFormat(OutputFormat.MP4_VIDEO)
                            }
                        )
                        OutputChoiceButton(
                            label = "MP3",
                            selected = state.selectedFormat == OutputFormat.MP3_AUDIO,
                            enabled = !state.isDownloading,
                            modifier = Modifier.weight(1f),
                            onClick = {
                                viewModel.setOutputFormat(OutputFormat.MP3_AUDIO)
                            }
                        )
                        OutputChoiceButton(
                            label = "WAV",
                            selected = state.selectedFormat == OutputFormat.WAV_AUDIO,
                            enabled = !state.isDownloading,
                            modifier = Modifier.weight(1f),
                            onClick = {
                                viewModel.setOutputFormat(OutputFormat.WAV_AUDIO)
                            }
                        )
                    }

                    if (state.selectedFormat == OutputFormat.MP4_VIDEO) {
                        Text(
                            text = "Video quality",
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 14.sp
                        )

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            DownloadViewModel.VIDEO_QUALITIES.forEach { quality ->
                                OutputChoiceButton(
                                    label = quality,
                                    selected = state.videoQuality == quality,
                                    enabled = !state.isDownloading,
                                    modifier = Modifier.weight(1f),
                                    onClick = { viewModel.setVideoQuality(quality) }
                                )
                            }
                        }
                    } else {
                        Card(
                            colors = CardDefaults.cardColors(
                                containerColor = Color(0xFF13161C)
                            ),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 14.dp, vertical = 12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Audio quality",
                                    color = muted,
                                    fontSize = 13.sp
                                )
                                Text(
                                    text = qualityText,
                                    fontWeight = FontWeight.SemiBold,
                                    fontSize = 13.sp
                                )
                            }
                        }
                    }

                    Button(
                        onClick = onDownload,
                        enabled = !state.isDownloading,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = accent)
                    ) {
                        Text(
                            text = downloadButtonText,
                            modifier = Modifier.padding(vertical = 5.dp),
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            Card(
                colors = CardDefaults.cardColors(containerColor = card),
                shape = RoundedCornerShape(18.dp)
            ) {
                Column(
                    modifier = Modifier.padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Status", fontWeight = FontWeight.SemiBold)
                        Text(
                            text = statusBadge,
                            color = statusBadgeColor,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }

                    Text(
                        text = state.status,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 14.sp
                    )

                    state.engineVersion?.let { version ->
                        Text(
                            text = "yt-dlp engine: $version",
                            color = muted,
                            fontSize = 12.sp
                        )
                    }

                    LinearProgressIndicator(
                        progress = { state.progress / 100f },
                        modifier = Modifier.fillMaxWidth(),
                        color = accent,
                        trackColor = Color(0xFF272D37)
                    )

                    if (state.isDownloading) {
                        val eta = state.etaSeconds
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = "${state.progress.toInt()}%",
                                color = muted,
                                fontSize = 13.sp
                            )
                            if (eta != null) {
                                Text(
                                    text = "ETA ${formatEta(eta)}",
                                    color = muted,
                                    fontSize = 13.sp
                                )
                            }
                        }

                        OutlinedButton(
                            onClick = viewModel::cancelDownload,
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("Cancel")
                        }
                    }

                    state.savedFileName?.let { name ->
                        Text(
                            text = "Saved: $name",
                            color = Color(0xFF55C989),
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            text = "Downloads/YouTube Downloader",
                            color = muted,
                            fontSize = 13.sp
                        )
                    }

                    state.error?.let { message ->
                        Text(
                            text = message,
                            color = MaterialTheme.colorScheme.error,
                            fontSize = 13.sp
                        )
                    }
                }
            }

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF13161C)),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        text = "Output details",
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "• MP4: H.264 + AAC, 1080p / 720p / 480p\n" +
                            "• MP3: 320 kbps audio\n" +
                            "• WAV: uncompressed PCM audio\n" +
                            "• Saves to Downloads/YouTube Downloader",
                        color = muted,
                        fontSize = 13.sp,
                        lineHeight = 20.sp
                    )
                }
            }

            Text(
                text = "Only download media you own or are authorised to use.",
                color = muted,
                fontSize = 12.sp,
                modifier = Modifier.padding(horizontal = 2.dp, vertical = 4.dp)
            )
        }
    }
}

@Composable
private fun OutputChoiceButton(
    label: String,
    selected: Boolean,
    enabled: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    if (selected) {
        Button(
            onClick = onClick,
            enabled = enabled,
            modifier = modifier,
            shape = RoundedCornerShape(11.dp)
        ) {
            Text(label, fontWeight = FontWeight.Bold)
        }
    } else {
        OutlinedButton(
            onClick = onClick,
            enabled = enabled,
            modifier = modifier,
            shape = RoundedCornerShape(11.dp)
        ) {
            Text(label)
        }
    }
}

private fun formatEta(seconds: Long): String {
    if (seconds < 0) return "—"
    val minutes = seconds / 60
    val remaining = seconds % 60
    return if (minutes > 0) "${minutes}m ${remaining}s" else "${remaining}s"
}
