package com.axon.vaxon.wake

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.axon.vaxon.MainActivity
import com.axon.vaxon.R
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread

/**
 * Foreground wake listener scaffold.
 *
 * Privacy contract (scaffold):
 * - Pre-wake audio is intended to stay in a local ring buffer only.
 * - No proprietary wake model is bundled yet; [StubLocalWakeDetector] only logs and fires callbacks.
 * - Privacy mute stops capture hooks without tearing down the persistent notification.
 */
class WakeWordForegroundService : Service() {

    private val muted = AtomicBoolean(false)
    private val running = AtomicBoolean(false)
    private var detectorThread: Thread? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopListening()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_MUTE -> {
                muted.set(true)
                notifyCallbacks { it.onPrivacyMuteChanged(true) }
                startForeground(NOTIFICATION_ID, buildNotification(muted = true))
            }
            ACTION_UNMUTE -> {
                muted.set(false)
                notifyCallbacks { it.onPrivacyMuteChanged(false) }
                startForeground(NOTIFICATION_ID, buildNotification(muted = false))
            }
            else -> {
                // ACTION_START or null / restart
                muted.set(false)
                startForeground(NOTIFICATION_ID, buildNotification(muted = false))
                startListening()
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        stopListening()
        super.onDestroy()
    }

    private fun startListening() {
        if (!running.compareAndSet(false, true)) return
        Log.i(TAG, "stub local wake armed (no proprietary model)")
        notifyCallbacks { it.onListeningChanged(true) }
        detectorThread = thread(name = "vaxon-stub-wake", isDaemon = true) {
            val detector = StubLocalWakeDetector(
                isMuted = { muted.get() },
                onWakeCandidate = { phrase ->
                    Log.i(TAG, "stub wake candidate: $phrase")
                    notifyCallbacks { it.onWakeCandidate(phrase) }
                },
            )
            while (running.get()) {
                detector.tick()
                try {
                    Thread.sleep(STUB_TICK_MS)
                } catch (_: InterruptedException) {
                    break
                }
            }
        }
    }

    private fun stopListening() {
        if (!running.compareAndSet(true, false)) return
        detectorThread?.interrupt()
        detectorThread = null
        Log.i(TAG, "stub local wake disarmed")
        notifyCallbacks { it.onListeningChanged(false) }
    }

    private fun buildNotification(muted: Boolean): Notification {
        val launch = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val title = if (muted) {
            getString(R.string.wake_notification_muted)
        } else {
            getString(R.string.wake_notification_title)
        }
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(getString(R.string.wake_notification_body))
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(launch)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(Notification.CATEGORY_SERVICE)
            .build()
    }

    companion object {
        const val CHANNEL_ID = "vaxon_wake"
        const val NOTIFICATION_ID = 4201
        const val ACTION_START = "com.axon.vaxon.wake.START"
        const val ACTION_STOP = "com.axon.vaxon.wake.STOP"
        const val ACTION_MUTE = "com.axon.vaxon.wake.MUTE"
        const val ACTION_UNMUTE = "com.axon.vaxon.wake.UNMUTE"

        private const val TAG = "WakeWordFg"
        private const val STUB_TICK_MS = 5_000L

        private val callbacks = CopyOnWriteArrayList<WakeCallback>()

        fun addCallback(callback: WakeCallback) {
            callbacks.addIfAbsent(callback)
        }

        fun removeCallback(callback: WakeCallback) {
            callbacks.remove(callback)
        }

        private fun notifyCallbacks(block: (WakeCallback) -> Unit) {
            callbacks.forEach { runCatching { block(it) } }
        }
    }

    fun interface WakeCallback {
        fun onWakeCandidate(phrase: String)
        fun onListeningChanged(listening: Boolean) {}
        fun onPrivacyMuteChanged(muted: Boolean) {}
    }
}

/**
 * Placeholder local wake detector. Logs ticks and occasionally emits a synthetic candidate.
 * Replace with an on-device model later; do not upload pre-wake PCM from here.
 */
internal class StubLocalWakeDetector(
    private val isMuted: () -> Boolean,
    private val onWakeCandidate: (String) -> Unit,
) {
    private var ticks = 0

    fun tick() {
        if (isMuted()) {
            Log.d(TAG, "stub wake tick skipped (privacy mute)")
            return
        }
        ticks += 1
        Log.d(TAG, "stub wake tick=$ticks (local ring buffer only; not uploaded)")
        if (ticks % 12 == 0) {
            onWakeCandidate("hey kairo (stub)")
        }
    }

    companion object {
        private const val TAG = "StubLocalWake"
    }
}
