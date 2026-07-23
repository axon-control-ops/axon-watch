package com.axon.vaxon.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun ReceiptsScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Receipts", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Stub: delivery / action receipts from the control plane will list here.",
            style = MaterialTheme.typography.bodyMedium,
        )
        Text("No receipts yet.", style = MaterialTheme.typography.bodySmall)
    }
}
