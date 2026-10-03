package com.example.harish333c.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.harish333c.databinding.FragmentDashboardBinding
import com.example.harish333c.network.ApiClient
import kotlinx.coroutines.launch

class DashboardFragment : Fragment() {

    private var _binding: FragmentDashboardBinding? = null
    private val binding get() = _binding!!

    var onNavigateToCompare: (() -> Unit)? = null
    var onNavigateToStats: (() -> Unit)? = null

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentDashboardBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnStartCompare.setOnClickListener {
            onNavigateToCompare?.invoke()
        }

        binding.btnViewStats.setOnClickListener {
            onNavigateToStats?.invoke()
        }

        loadDashboardData()
    }

    fun loadDashboardData() {
        if (_binding == null) return

        lifecycleScope.launch {
            try {
                // 1. Fetch Backend API status
                val statusResp = ApiClient.getService().getStatus()
                if (statusResp.isSuccessful && statusResp.body() != null) {
                    val status = statusResp.body()!!
                    if (!status.apiKeyConfigured) {
                        binding.cardApiKeyAlert.visibility = View.VISIBLE
                        binding.tvApiKeyNoticeText.text = status.message ?: "API Key missing in backend/.env. Operating in realistic benchmark mode."
                    } else {
                        binding.cardApiKeyAlert.visibility = View.GONE
                    }
                }

                // 2. Fetch Accuracy Stats
                val statsResp = ApiClient.getService().getStats()
                if (statsResp.isSuccessful && statsResp.body() != null) {
                    val stats = statsResp.body()!!
                    binding.tvPlainLlmAccuracy.text = "${stats.plainLlmAccuracyPct}%"
                    binding.tvPlainLlmCount.text = "${stats.plainLlmCorrectCount}/${stats.totalEvaluated} Correct"

                    binding.tvRagAccuracy.text = "${stats.ragAccuracyPct}%"
                    binding.tvRagCount.text = "${stats.ragCorrectCount}/${stats.totalEvaluated} Correct"

                    val gain = stats.accuracyImprovementPct
                    val gainText = if (gain >= 0) "+${gain}% Gain" else "${gain}%"
                    binding.tvAccuracyGain.text = gainText

                    val maxProgress = 100
                    val currentGainProgress = stats.ragAccuracyPct.toInt().coerceIn(0, maxProgress)
                    binding.progressRagGain.progress = currentGainProgress
                }
            } catch (e: Exception) {
                // Ignore network error gracefully on setup
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
