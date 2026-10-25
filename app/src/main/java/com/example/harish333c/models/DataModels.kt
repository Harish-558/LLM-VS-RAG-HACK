package com.example.harish333c.models

import com.google.gson.annotations.SerializedName

data class CompareRequest(
    val question: String
)

data class RetrievedDoc(
    val id: String?,
    val title: String,
    val category: String?,
    val content: String,
    @SerializedName("relevance_score")
    val relevanceScore: Float,
    val page: Int? = null
)

data class CompareResponse(
    val id: String,
    val question: String,
    @SerializedName("plain_llm_answer")
    val plainLlmAnswer: String,
    @SerializedName("plain_llm_latency_ms")
    val plainLlmLatencyMs: Int,
    @SerializedName("rag_answer")
    val ragAnswer: String,
    @SerializedName("rag_latency_ms")
    val ragLatencyMs: Int,
    @SerializedName("retrieved_docs")
    val retrievedDocs: List<RetrievedDoc>,
    @SerializedName("api_key_configured")
    val apiKeyConfigured: Boolean
)

data class EvaluateRequest(
    @SerializedName("comparison_id")
    val comparisonId: String,
    val question: String,
    @SerializedName("plain_llm_correct")
    val plainLlmCorrect: Boolean,
    @SerializedName("rag_correct")
    val ragCorrect: Boolean
)

data class StatsResponse(
    @SerializedName("total_evaluated")
    val totalEvaluated: Int,
    @SerializedName("plain_llm_correct_count")
    val plainLlmCorrectCount: Int,
    @SerializedName("rag_correct_count")
    val ragCorrectCount: Int,
    @SerializedName("plain_llm_accuracy_pct")
    val plainLlmAccuracyPct: Float,
    @SerializedName("rag_accuracy_pct")
    val ragAccuracyPct: Float,
    @SerializedName("accuracy_improvement_pct")
    val accuracyImprovementPct: Float
)

data class SampleQuestion(
    val id: String,
    val category: String,
    val question: String
)

data class ApiStatusResponse(
    val status: String,
    @SerializedName("api_key_configured")
    val apiKeyConfigured: Boolean,
    @SerializedName("documents_count")
    val documentsCount: Int,
    @SerializedName("faiss_active")
    val faissActive: Boolean,
    val message: String?,
    @SerializedName("active_pdf")
    val activePdf: String? = null
)

data class PdfUploadResponse(
    val status: String,
    val filename: String,
    @SerializedName("pages_count")
    val pagesCount: Int,
    @SerializedName("chunks_count")
    val chunksCount: Int,
    @SerializedName("documents_total")
    val documentsTotal: Int,
    val message: String
)
