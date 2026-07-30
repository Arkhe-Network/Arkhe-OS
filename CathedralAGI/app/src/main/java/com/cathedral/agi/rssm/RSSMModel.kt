package com.cathedral.agi.rssm

import android.content.Context
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel

data class RSSMState(val deterministic: FloatArray, val stochastic: FloatArray)

class RSSMModel(context: Context) {
    private val interpreter: Interpreter
    private var state = RSSMState(FloatArray(256), FloatArray(32))

    init {
        val modelBuffer = loadModelFile(context, "rssm_model.tflite")
        interpreter = Interpreter(modelBuffer)
    }

    private fun loadModelFile(context: Context, filename: String): MappedByteBuffer {
        val assetFileDescriptor = context.assets.openFd(filename)
        val inputStream = FileInputStream(assetFileDescriptor.fileDescriptor)
        val fileChannel = inputStream.channel
        val startOffset = assetFileDescriptor.startOffset
        val declaredLength = assetFileDescriptor.declaredLength
        return fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
    }

    fun forward(vision: FloatArray, action: FloatArray): FloatArray {
        val input = arrayOf(vision, action, state.deterministic, state.stochastic)
        val output = Array(1) { FloatArray(288) }
        interpreter.run(input, output)
        val newDeter = output[0].sliceArray(0 until 256)
        val newStoch = output[0].sliceArray(256 until 288)
        state = RSSMState(newDeter, newStoch)
        return output[0]
    }

    fun close() {
        interpreter.close()
    }
}