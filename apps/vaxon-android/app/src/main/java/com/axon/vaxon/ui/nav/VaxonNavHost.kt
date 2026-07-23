package com.axon.vaxon.ui.nav

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.axon.vaxon.ui.screens.ApprovalsScreen
import com.axon.vaxon.ui.screens.ConversationScreen
import com.axon.vaxon.ui.screens.EnrollmentScreen
import com.axon.vaxon.ui.screens.PrivacyMicStatusScreen
import com.axon.vaxon.ui.screens.ReceiptsScreen

enum class VaxonDestination(val route: String, val label: String) {
    Enrollment("enrollment", "Enroll"),
    Privacy("privacy", "Privacy"),
    Conversation("conversation", "Talk"),
    Approvals("approvals", "Approve"),
    Receipts("receipts", "Receipts"),
}

@Composable
fun VaxonNavHost() {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val current = backStackEntry?.destination

    Scaffold(
        bottomBar = {
            NavigationBar {
                VaxonDestination.entries.forEach { dest ->
                    NavigationBarItem(
                        selected = current?.hierarchy?.any { it.route == dest.route } == true,
                        onClick = {
                            navController.navigate(dest.route) {
                                popUpTo(navController.graph.startDestinationId) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Text(dest.label.take(1)) },
                        label = { Text(dest.label) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = VaxonDestination.Enrollment.route,
            modifier = Modifier.padding(padding),
        ) {
            composable(VaxonDestination.Enrollment.route) { EnrollmentScreen() }
            composable(VaxonDestination.Privacy.route) { PrivacyMicStatusScreen() }
            composable(VaxonDestination.Conversation.route) { ConversationScreen() }
            composable(VaxonDestination.Approvals.route) { ApprovalsScreen() }
            composable(VaxonDestination.Receipts.route) { ReceiptsScreen() }
        }
    }
}
