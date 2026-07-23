package com.axon.vaxon.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF0B3D2E),
    secondary = Color(0xFF1F6F5B),
    tertiary = Color(0xFFC4A35A),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF7DCEA0),
    secondary = Color(0xFF52B788),
    tertiary = Color(0xFFE6C87A),
)

@Composable
fun VaxonTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
