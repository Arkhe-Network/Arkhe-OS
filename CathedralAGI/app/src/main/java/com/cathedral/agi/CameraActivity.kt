package com.cathedral.agi

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.*
import android.os.Bundle
import android.view.SurfaceView
import android.widget.ImageView
import android.widget.Toast
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.cathedral.agi.detection.YOLODetector
import com.cathedral.agi.rssm.RSSMModel
import com.cathedral.agi.safety.SafetyEngine
import com.cathedral.agi.memory.EpisodicMemory
import kotlinx.coroutines.*
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet

class CameraActivity : AppCompatActivity() {
    private lateinit var imageView: ImageView
    private lateinit var chartView: LineChart
    private lateinit var cameraExecutor: ExecutorService

    // Cathedral modules
    private lateinit var yolo: YOLODetector
    private lateinit var rssm: RSSMModel
    private lateinit var safety: SafetyEngine
    private lateinit var memory: EpisodicMemory

    private val actionHistory = mutableListOf<FloatArray>()
    private val actionSeries = mutableListOf<Entry>()
    private var currentActionIndex = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_camera)

        imageView = findViewById(R.id.iv_preview)
        chartView = findViewById(R.id.chart_action)

        // Request camera permission
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 100)
        } else {
            startCamera()
        }

        // Initialize modules
        yolo = YOLODetector(this)
        rssm = RSSMModel(this)
        safety = SafetyEngine()
        memory = EpisodicMemory(this)

        cameraExecutor = Executors.newSingleThreadExecutor()
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build()
            val imageAnalysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
            imageAnalysis.setAnalyzer(cameraExecutor, ImageAnalysis.Analyzer { imageProxy ->
                val bitmap = imageProxyToBitmap(imageProxy)
                imageProxy.close()
                runOnUiThread {
                    processFrame(bitmap)
                }
            })
            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
            cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalysis)
        }, ContextCompat.getMainExecutor(this))
    }

    private fun imageProxyToBitmap(imageProxy: ImageProxy): Bitmap {
        val buffer = imageProxy.planes[0].buffer
        val bytes = ByteArray(buffer.remaining())
        buffer.get(bytes)
        val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        return Bitmap.createScaledBitmap(bitmap, 640, 640, true)
    }

    private fun processFrame(bitmap: Bitmap) {
        // 1. YOLO detection
        val detections = yolo.detect(bitmap)
        val targetId = detections.firstOrNull()?.label ?: "unknown"
        val force = 0.5f // placeholder

        // 2. RSSM forward (vision features from YOLO + last action)
        val visionFeatures = FloatArray(256) // placeholder: extract from YOLO features
        val lastAction = if (actionHistory.isNotEmpty()) actionHistory.last() else FloatArray(4) { 0f }
        val state = rssm.forward(visionFeatures, lastAction)

        // 3. Fast brain action (random for now, but would use policy network)
        val action = FloatArray(4) { (Math.random() * 2 - 1).toFloat() }

        // 4. Safety check
        val safe = safety.isSafe(action, targetId, force)
        if (!safe) {
            Toast.makeText(this, "Ação insegura bloqueada!", Toast.LENGTH_SHORT).show()
            return
        }

        // 5. Store memory
        memory.store(state, action, targetId)

        // 6. Update UI: bounding boxes
        drawBoundingBoxes(bitmap, detections, action)

        // 7. Update action chart
        updateActionChart(action)

        // 8. Optional slow brain call when confidence low
        // if (confidence < 0.3) callSlowBrainAsync(dilemma)
    }

    private fun drawBoundingBoxes(bitmap: Bitmap, detections: List<Detection>, action: FloatArray) {
        val canvas = Canvas(bitmap)
        val paint = Paint().apply {
            color = Color.RED
            strokeWidth = 5f
            style = Paint.Style.STROKE
        }
        val textPaint = Paint().apply {
            color = Color.WHITE
            textSize = 24f
        }
        for (det in detections) {
            canvas.drawRect(det.x1, det.y1, det.x2, det.y2, paint)
            canvas.drawText(det.label, det.x1, det.y1 - 10, textPaint)
        }
        // Draw action vector as text overlay
        val actionStr = "Action: [${action.joinToString(", ") { "%.2f".format(it) }}]"
        canvas.drawText(actionStr, 20f, 80f, textPaint)
        imageView.setImageBitmap(bitmap)
    }

    private fun updateActionChart(action: FloatArray) {
        actionHistory.add(action)
        val entry = Entry(currentActionIndex++, action[0]) // plot first dimension
        actionSeries.add(entry)
        val dataSet = LineDataSet(actionSeries, "Action X")
        val lineData = LineData(dataSet)
        chartView.data = lineData
        chartView.notifyDataSetChanged()
        chartView.invalidate()
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
        rssm.close()
        yolo.close()
    }
}