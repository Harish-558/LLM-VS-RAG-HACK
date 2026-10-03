package com.example.harish333c.network

import com.example.harish333c.models.*
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface ApiService {

    @GET("api/status")
    suspend fun getStatus(): Response<ApiStatusResponse>

    @GET("api/sample-questions")
    suspend fun getSampleQuestions(): Response<List<SampleQuestion>>

    @POST("api/compare")
    suspend fun compare(@Body request: CompareRequest): Response<CompareResponse>

    @POST("api/evaluate")
    suspend fun evaluate(@Body request: EvaluateRequest): Response<StatsResponse>

    @GET("api/stats")
    suspend fun getStats(): Response<StatsResponse>
}
