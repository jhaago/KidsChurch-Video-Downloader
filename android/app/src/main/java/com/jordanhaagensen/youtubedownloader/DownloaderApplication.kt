package com.jordanhaagensen.youtubedownloader

import android.app.Application
import android.util.Log
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL

class DownloaderApplication : Application() {
    override fun onCreate() {
        super.onCreate()

        try {
            YoutubeDL.getInstance().init(this)
            FFmpeg.getInstance().init(this)
            DownloaderRuntime.markReady()
        } catch (t: Throwable) {
            Log.e("YouTubeDownloader", "Failed to initialise download engine", t)
            DownloaderRuntime.markFailed(t.message ?: t.javaClass.simpleName)
        }
    }
}

object DownloaderRuntime {
    @Volatile
    var ready: Boolean = false
        private set

    @Volatile
    var error: String? = null
        private set

    fun markReady() {
        ready = true
        error = null
    }

    fun markFailed(message: String) {
        ready = false
        error = message
    }
}
