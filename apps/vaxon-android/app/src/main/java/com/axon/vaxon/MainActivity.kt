package com.axon.vaxon

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.axon.vaxon.ui.nav.VaxonNavHost
import com.axon.vaxon.ui.theme.VaxonTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            VaxonTheme {
                VaxonNavHost()
            }
        }
    }
}
