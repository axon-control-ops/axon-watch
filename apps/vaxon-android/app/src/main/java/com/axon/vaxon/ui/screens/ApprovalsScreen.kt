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
fun ApprovalsScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Approvals", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Stub: pending step-up / host actions will surface here for mobile confirm.",
            style = MaterialTheme.typography.bodyMedium,
        )
        Text("No pending approvals.", style = MaterialTheme.typography.bodySmall)
    }
}
