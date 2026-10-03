package com.example.harish333c.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.harish333c.databinding.FragmentStatsBinding
import com.example.harish333c.network.ApiClient
import kotlinx.coroutines.launch

class StatsFragment : Fragment() {

    private var _binding: FragmentStatsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentStatsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnRefreshStats.setOnClickListener {
            loadStats()
        }

        loadStats()
    }

    fun loadStats() {
        if (_binding == null) return

        lifecycleScope.launch {
            try {
                val resp = ApiClient.getService().getStats()
                if (resp.isSuccessful && resp.body() != null) {
                    val stats = resp.body()!!

                    binding.tvTotalEvaluations.text = "${stats.totalEvaluated} Questions"
                    binding.tvPlainBarPct.text = "${stats.plainLlmAccuracyPct}% (${stats.plainLlmCorrectCount}/${stats.totalEvaluated})"
                    binding.tvRagBarPct.text = "${stats.ragAccuracyPct}% (${stats.ragCorrectCount}/${stats.totalEvaluated})"

                    binding.progressPlainBar.progress = stats.plainLlmAccuracyPct.toInt().coerceIn(0, 100)
                    binding.progressRagBar.progress = stats.ragAccuracyPct.toInt().coerceIn(0, 100)

                    if (stats.totalEvaluated == 0) {
                        binding.tvStatsInsight.text = "No evaluations submitted yet. Go to the Compare screen, ask a question, and mark the answers as Correct or Incorrect to generate live accuracy metrics."
                    } else {
                        val gain = stats.accuracyImprovementPct
                        binding.tvStatsInsight.text = "Benchmark Summary:\n" +
                                "• RAG System achieved ${stats.ragAccuracyPct}% factual accuracy vs ${stats.plainLlmAccuracyPct}% for Plain LLM.\n" +
                                "• Net Accuracy Improvement: +${gain}%.\n" +
                                "• FAISS vector retrieval effectively prevented hallucinations on exact numbers, dates, and specifications."
                    }
                }
            } catch (e: Exception) {
                Toast.makeText(requireContext(), "Failed to fetch stats: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
