package com.example.harish333c.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.harish333c.R
import com.example.harish333c.databinding.FragmentCompareBinding
import com.example.harish333c.databinding.ItemKnowledgeDocBinding
import com.example.harish333c.models.*
import com.example.harish333c.network.ApiClient
import com.google.android.material.chip.Chip
import kotlinx.coroutines.launch

class CompareFragment : Fragment() {

    private var _binding: FragmentCompareBinding? = null
    private val binding get() = _binding!!

    private var currentComparison: CompareResponse? = null
    private var isPlainCorrect: Boolean? = null
    private var isRagCorrect: Boolean? = null
    private var isContextExpanded: Boolean = false

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentCompareBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnRunComparison.setOnClickListener {
            val q = binding.etQuestionInput.text.toString().trim()
            if (q.isEmpty()) {
                Toast.makeText(requireContext(), "Please enter a question", Toast.LENGTH_SHORT).show()
            } else {
                runComparison(q)
            }
        }

        binding.layoutToggleContext.setOnClickListener {
            isContextExpanded = !isContextExpanded
            binding.layoutRetrievedDocsContainer.visibility = if (isContextExpanded) View.VISIBLE else View.GONE
            binding.tvToggleContextState.text = if (isContextExpanded) "Hide ▲" else "Show ▼"
        }

        setupEvaluationButtons()
        fetchSampleQuestions()
    }

    private fun setupEvaluationButtons() {
        binding.btnPlainCorrect.setOnClickListener {
            isPlainCorrect = true
            updateButtonStyles()
        }

        binding.btnPlainIncorrect.setOnClickListener {
            isPlainCorrect = false
            updateButtonStyles()
        }

        binding.btnRagCorrect.setOnClickListener {
            isRagCorrect = true
            updateButtonStyles()
        }

        binding.btnRagIncorrect.setOnClickListener {
            isRagCorrect = false
            updateButtonStyles()
        }

        binding.btnSubmitEval.setOnClickListener {
            submitEvaluation()
        }
    }

    private fun updateButtonStyles() {
        // Plain LLM buttons
        if (isPlainCorrect == true) {
            binding.btnPlainCorrect.setBackgroundColor(ContextCompat.getColor(requireContext(), R.color.success_green))
            binding.btnPlainCorrect.setTextColor(ContextCompat.getColor(requireContext(), R.color.bg_dark_navy))
            binding.btnPlainIncorrect.setBackgroundColor(ContextCompat.getColor(requireContext(), android.R.color.transparent))
            binding.btnPlainIncorrect.setTextColor(ContextCompat.getColor(requireContext(), R.color.error_red))
        } else if (isPlainCorrect == false) {
            binding.btnPlainIncorrect.setBackgroundColor(ContextCompat.getColor(requireContext(), R.color.error_red))
            binding.btnPlainIncorrect.setTextColor(ContextCompat.getColor(requireContext(), R.color.white))
            binding.btnPlainCorrect.setBackgroundColor(ContextCompat.getColor(requireContext(), android.R.color.transparent))
            binding.btnPlainCorrect.setTextColor(ContextCompat.getColor(requireContext(), R.color.success_green))
        }

        // RAG buttons
        if (isRagCorrect == true) {
            binding.btnRagCorrect.setBackgroundColor(ContextCompat.getColor(requireContext(), R.color.success_green))
            binding.btnRagCorrect.setTextColor(ContextCompat.getColor(requireContext(), R.color.bg_dark_navy))
            binding.btnRagIncorrect.setBackgroundColor(ContextCompat.getColor(requireContext(), android.R.color.transparent))
            binding.btnRagIncorrect.setTextColor(ContextCompat.getColor(requireContext(), R.color.error_red))
        } else if (isRagCorrect == false) {
            binding.btnRagIncorrect.setBackgroundColor(ContextCompat.getColor(requireContext(), R.color.error_red))
            binding.btnRagIncorrect.setTextColor(ContextCompat.getColor(requireContext(), R.color.white))
            binding.btnRagCorrect.setBackgroundColor(ContextCompat.getColor(requireContext(), android.R.color.transparent))
            binding.btnRagCorrect.setTextColor(ContextCompat.getColor(requireContext(), R.color.success_green))
        }
    }

    private fun fetchSampleQuestions() {
        lifecycleScope.launch {
            try {
                val resp = ApiClient.getService().getSampleQuestions()
                if (resp.isSuccessful && resp.body() != null) {
                    val samples = resp.body()!!
                    binding.chipGroupSamples.removeAllViews()
                    for (sample in samples) {
                        val chip = Chip(requireContext()).apply {
                            text = "${sample.category}: ${sample.question.take(30)}..."
                            isCheckable = false
                            setChipBackgroundColorResource(R.color.card_navy_surface)
                            setTextColor(ContextCompat.getColor(requireContext(), R.color.primary_teal))
                            setOnClickListener {
                                binding.etQuestionInput.setText(sample.question)
                                runComparison(sample.question)
                            }
                        }
                        binding.chipGroupSamples.addView(chip)
                    }
                }
            } catch (e: Exception) {
                // Ignore network error
            }
        }
    }

    private fun runComparison(question: String) {
        binding.progressLoading.visibility = View.VISIBLE
        binding.btnRunComparison.isEnabled = false
        binding.layoutComparisonResults.visibility = View.GONE
        isPlainCorrect = null
        isRagCorrect = null
        updateButtonStyles()

        lifecycleScope.launch {
            try {
                val resp = ApiClient.getService().compare(CompareRequest(question))
                binding.progressLoading.visibility = View.GONE
                binding.btnRunComparison.isEnabled = true

                if (resp.isSuccessful && resp.body() != null) {
                    val data = resp.body()!!
                    currentComparison = data

                    binding.tvQuestionTitle.text = "Question: ${data.question}"
                    binding.tvPlainLlmAnswerText.text = data.plainLlmAnswer
                    binding.tvPlainLatency.text = "${data.plainLlmLatencyMs} ms"

                    binding.tvRagAnswerText.text = data.ragAnswer
                    binding.tvRagLatency.text = "${data.ragLatencyMs} ms"

                    // Populate Knowledge Context docs
                    binding.layoutRetrievedDocsContainer.removeAllViews()
                    val inflater = LayoutInflater.from(requireContext())
                    for (doc in data.retrievedDocs) {
                        val docBinding = ItemKnowledgeDocBinding.inflate(inflater, binding.layoutRetrievedDocsContainer, false)
                        docBinding.tvDocTitle.text = "[${doc.category}] ${doc.title}"
                        docBinding.tvRelevanceScore.text = "FAISS Score: ${doc.relevanceScore}"
                        docBinding.tvDocContent.text = doc.content
                        binding.layoutRetrievedDocsContainer.addView(docBinding.root)
                    }

                    binding.layoutComparisonResults.visibility = View.VISIBLE
                } else {
                    Toast.makeText(requireContext(), "Failed to run comparison. Check server.", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                binding.progressLoading.visibility = View.GONE
                binding.btnRunComparison.isEnabled = true
                Toast.makeText(requireContext(), "Error: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun submitEvaluation() {
        val cmp = currentComparison ?: run {
            Toast.makeText(requireContext(), "No active comparison to evaluate", Toast.LENGTH_SHORT).show()
            return
        }

        if (isPlainCorrect == null || isRagCorrect == null) {
            Toast.makeText(requireContext(), "Please mark both Plain LLM and RAG answers as Correct or Incorrect first.", Toast.LENGTH_LONG).show()
            return
        }

        lifecycleScope.launch {
            try {
                val req = EvaluateRequest(
                    comparisonId = cmp.id,
                    question = cmp.question,
                    plainLlmCorrect = isPlainCorrect!!,
                    ragCorrect = isRagCorrect!!
                )
                val resp = ApiClient.getService().evaluate(req)
                if (resp.isSuccessful) {
                    Toast.makeText(requireContext(), "✓ Evaluation recorded! Accuracy stats updated.", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(requireContext(), "Failed to record evaluation: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
