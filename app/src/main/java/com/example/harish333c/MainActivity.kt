package com.example.harish333c

import android.app.AlertDialog
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.harish333c.databinding.ActivityMainBinding
import com.example.harish333c.network.ApiClient
import com.example.harish333c.ui.CompareFragment
import com.example.harish333c.ui.DashboardFragment
import com.example.harish333c.ui.StatsFragment
import com.google.android.material.button.MaterialButton
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    private val dashboardFragment by lazy { DashboardFragment() }
    private val compareFragment by lazy { CompareFragment() }
    private val statsFragment by lazy { StatsFragment() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        ViewCompat.setOnApplyWindowInsetsListener(binding.main) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        // Setup Fragment navigation callbacks
        dashboardFragment.onNavigateToCompare = {
            binding.bottomNav.selectedItemId = R.id.nav_compare
        }
        dashboardFragment.onNavigateToStats = {
            binding.bottomNav.selectedItemId = R.id.nav_stats
        }

        // Bottom Navigation Listener
        binding.bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_dashboard -> {
                    switchFragment(dashboardFragment)
                    dashboardFragment.loadDashboardData()
                    true
                }
                R.id.nav_compare -> {
                    switchFragment(compareFragment)
                    true
                }
                R.id.nav_stats -> {
                    switchFragment(statsFragment)
                    statsFragment.loadStats()
                    true
                }
                else -> false
            }
        }

        // Settings Dialog Button
        binding.btnSettings.setOnClickListener {
            showSettingsDialog()
        }

        // Load saved base URL if previously configured in Settings
        val prefs = getSharedPreferences("app_settings", MODE_PRIVATE)
        val savedUrl = prefs.getString("backend_url", null)
        if (!savedUrl.isNullOrEmpty()) {
            ApiClient.setBaseUrl(savedUrl)
        }

        // Default screen
        switchFragment(dashboardFragment)

        // Check backend server connection
        checkBackendStatus()
    }

    private fun switchFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, fragment)
            .commit()
    }

    private fun checkBackendStatus() {
        lifecycleScope.launch {
            try {
                val resp = ApiClient.getService().getStatus()
                if (resp.isSuccessful && resp.body() != null) {
                    val status = resp.body()!!
                    binding.statusDot.background = ContextCompat.getDrawable(this@MainActivity, R.drawable.bg_teal_badge)
                    if (status.apiKeyConfigured) {
                        binding.tvServerStatus.text = "Backend Online (FAISS: ${status.documentsCount} Docs)"
                        binding.tvServerStatus.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.primary_teal))
                    } else {
                        binding.tvServerStatus.text = "Backend Online (Key Missing - Benchmark Mode)"
                        binding.tvServerStatus.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.secondary_orange))
                    }
                } else {
                    setOfflineStatus()
                }
            } catch (e: Exception) {
                setOfflineStatus()
            }
        }
    }

    private fun setOfflineStatus() {
        binding.statusDot.background = ContextCompat.getDrawable(this, R.drawable.bg_orange_badge)
        binding.tvServerStatus.text = "Backend Offline (${ApiClient.getBaseUrl().take(25)}...)"
        binding.tvServerStatus.setTextColor(ContextCompat.getColor(this, R.color.error_red))
    }

    private fun showSettingsDialog() {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_settings, null)
        val etUrl = dialogView.findViewById<EditText>(R.id.etBaseUrl)
        val tvResult = dialogView.findViewById<TextView>(R.id.tvTestConnectionResult)
        val btnTest = dialogView.findViewById<MaterialButton>(R.id.btnTestConnection)
        val btnSave = dialogView.findViewById<MaterialButton>(R.id.btnSaveSettings)

        etUrl.setText(ApiClient.getBaseUrl())

        val alertDialog = AlertDialog.Builder(this)
            .setView(dialogView)
            .create()

        btnTest.setOnClickListener {
            val testUrl = etUrl.text.toString().trim()
            if (testUrl.isEmpty()) return@setOnClickListener
            ApiClient.setBaseUrl(testUrl)
            tvResult.visibility = View.VISIBLE
            tvResult.text = "Testing connection..."
            tvResult.setTextColor(ContextCompat.getColor(this, R.color.text_secondary))

            lifecycleScope.launch {
                try {
                    val resp = ApiClient.getService().getStatus()
                    if (resp.isSuccessful && resp.body() != null) {
                        tvResult.text = "✓ Connection Successful! Backend active."
                        tvResult.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.success_green))
                    } else {
                        tvResult.text = "✗ Server returned code ${resp.code()}"
                        tvResult.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.error_red))
                    }
                } catch (e: Exception) {
                    tvResult.text = "✗ Failed to connect: ${e.localizedMessage}"
                    tvResult.setTextColor(ContextCompat.getColor(this@MainActivity, R.color.error_red))
                }
            }
        }

        btnSave.setOnClickListener {
            val newUrl = etUrl.text.toString().trim()
            if (newUrl.isNotEmpty()) {
                ApiClient.setBaseUrl(newUrl)
                getSharedPreferences("app_settings", MODE_PRIVATE)
                    .edit()
                    .putString("backend_url", ApiClient.getBaseUrl())
                    .apply()
                checkBackendStatus()
                dashboardFragment.loadDashboardData()
                Toast.makeText(this, "Base URL updated: ${ApiClient.getBaseUrl()}", Toast.LENGTH_SHORT).show()
                alertDialog.dismiss()
            }
        }

        alertDialog.show()
    }
}