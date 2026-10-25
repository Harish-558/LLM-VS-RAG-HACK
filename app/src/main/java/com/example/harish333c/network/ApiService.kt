package com.example.harish333c.network

import com.example.harish333c.models.*
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    @GET("api/status")
    suspend fun getStatus(): Response<ApiStatusResponse>

    @GET("api/sample-questions")
    suspend fun getSampleQuestions(): Response<List<SampleQuestion>>

    @POST("api/compare")
    suspend fun compare(@Body request: CompareRequest): Response<CompareResponse>

    @Multipart
    @POST("api/upload-pdf")
    suspend fun uploadPdf(@Part file: MultipartBody.Part): Response<PdfUploadResponse>

    @POST("api/reset-knowledge-base")
    suspend fun resetKnowledgeBase(): Response<ApiStatusResponse>

    @POST("api/evaluate")
    suspend fun evaluate(@Body request: EvaluateRequest): Response<StatsResponse>

    @GET("api/stats")
    suspend fun getStats(): Response<StatsResponse>
}
