package com.example.harish333c.ui

import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.harish333c.R
import com.example.harish333c.databinding.FragmentCompareBinding
import com.example.harish333c.databinding.ItemKnowledgeDocBinding
import com.example.harish333c.models.*
import com.example.harish333c.network.ApiClient
import com.google.android.material.chip.Chip
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

class CompareFragment : Fragment() {

    private var _binding: FragmentCompareBinding? = null
    private val binding get() = _binding!!

    private var currentComparison: CompareResponse? = null
    private var isPlainCorrect: Boolean? = null
    private var isRagCorrect: Boolean? = null
    private var isContextExpanded: Boolean = false

    private val pickPdfLauncher = registerForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let { uploadPdf(it) }
    }

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

        binding.btnUploadPdf.setOnClickListener {
            pickPdfLauncher.launch("application/pdf")
        }

        binding.btnResetKnowledge.setOnClickListener {
            resetKnowledgeBase()
        }

        fetchActiveStatus()
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
                        docBinding.tvDocTitle.text = "[${doc.category ?: "Doc"}] ${doc.title}"
                        docBinding.tvRelevanceScore.text = "FAISS Score: ${doc.relevanceScore}"
                        docBinding.tvDocContent.text = doc.content
                        if (doc.page != null) {
                            docBinding.tvDocPage.visibility = View.VISIBLE
                            docBinding.tvDocPage.text = "Page ${doc.page}"
                        } else {
                            docBinding.tvDocPage.visibility = View.GONE
                        }
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

    private fun fetchActiveStatus() {
        lifecycleScope.launch {
            try {
                val resp = ApiClient.getService().getStatus()
                if (resp.isSuccessful && resp.body() != null) {
                    val status = resp.body()!!
                    if (!status.activePdf.isNullOrEmpty()) {
                        binding.tvActiveKnowledgeSource.text = "📄 Active PDF: ${status.activePdf}"
                        binding.btnResetKnowledge.visibility = View.VISIBLE
                    } else {
                        binding.tvActiveKnowledgeSource.text = "Current: Built-in Knowledge Base (FAISS)"
                        binding.btnResetKnowledge.visibility = View.GONE
                    }
                }
            } catch (e: Exception) {
                // Ignore network error on setup
            }
        }
    }

    private fun uploadPdf(uri: Uri) {
        val fileName = getFileName(uri) ?: "document.pdf"
        binding.progressPdfUpload.visibility = View.VISIBLE
        binding.btnUploadPdf.isEnabled = false
        binding.tvPdfUploadStatus.visibility = View.GONE

        lifecycleScope.launch {
            try {
                val bytes = withContext(Dispatchers.IO) {
                    requireContext().contentResolver.openInputStream(uri)?.use { it.readBytes() }
                }

                if (bytes == null || bytes.isEmpty()) {
                    binding.progressPdfUpload.visibility = View.GONE
                    binding.btnUploadPdf.isEnabled = true
                    Toast.makeText(requireContext(), "Could not read PDF file", Toast.LENGTH_SHORT).show()
                    return@launch
                }

                val requestFile = bytes.toRequestBody("application/pdf".toMediaTypeOrNull())
                val body = MultipartBody.Part.createFormData("file", fileName, requestFile)

                val resp = ApiClient.getService().uploadPdf(body)
                binding.progressPdfUpload.visibility = View.GONE
                binding.btnUploadPdf.isEnabled = true

                if (resp.isSuccessful && resp.body() != null) {
                    val data = resp.body()!!
                    binding.tvActiveKnowledgeSource.text = "📄 Active PDF: ${data.filename} (${data.pagesCount} pgs, ${data.chunksCount} chunks)"
                    binding.btnResetKnowledge.visibility = View.VISIBLE
                    binding.tvPdfUploadStatus.visibility = View.VISIBLE
                    binding.tvPdfUploadStatus.text = "✓ Indexed ${data.chunksCount} sections from ${data.filename}"
                    binding.etQuestionInput.hint = "Ask a question about ${data.filename}..."
                    Toast.makeText(requireContext(), "PDF indexed into RAG successfully!", Toast.LENGTH_LONG).show()
                } else {
                    val err = resp.errorBody()?.string() ?: "Failed to upload"
                    Toast.makeText(requireContext(), "Upload error: $err", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                binding.progressPdfUpload.visibility = View.GONE
                binding.btnUploadPdf.isEnabled = true
                Toast.makeText(requireContext(), "Error uploading PDF: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun resetKnowledgeBase() {
        binding.progressPdfUpload.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val resp = ApiClient.getService().resetKnowledgeBase()
                binding.progressPdfUpload.visibility = View.GONE
                if (resp.isSuccessful) {
                    binding.tvActiveKnowledgeSource.text = "Current: Built-in Knowledge Base (FAISS)"
                    binding.btnResetKnowledge.visibility = View.GONE
                    binding.tvPdfUploadStatus.visibility = View.GONE
                    binding.etQuestionInput.hint = "e.g. What is the qubit count and gate fidelity of Quantum Nova-X Processor?"
                    Toast.makeText(requireContext(), "Reset to default knowledge base", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                binding.progressPdfUpload.visibility = View.GONE
                Toast.makeText(requireContext(), "Failed to reset: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun getFileName(uri: Uri): String? {
        var name: String? = null
        if (uri.scheme == "content") {
            try {
                requireContext().contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                    val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (nameIndex != -1 && cursor.moveToFirst()) {
                        name = cursor.getString(nameIndex)
                    }
                }
            } catch (e: Exception) {
                // fallback
            }
        }
        return name ?: uri.lastPathSegment ?: "document.pdf"
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
