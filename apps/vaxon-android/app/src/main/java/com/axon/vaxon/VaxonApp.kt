package com.axon.vaxon

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.axon.vaxon.wake.WakeWordForegroundService

class VaxonApp : Application() {
    override fun onCreate() {
        super.onCreate()
        ensureWakeNotificationChannel()
    }

    private fun ensureWakeNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java) ?: return
        val channel = NotificationChannel(
            WakeWordForegroundService.CHANNEL_ID,
            getString(R.string.wake_notification_channel),
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = "Persistent notification while local wake listening is armed"
            setShowBadge(false)
        }
        manager.createNotificationChannel(channel)
    }
}
