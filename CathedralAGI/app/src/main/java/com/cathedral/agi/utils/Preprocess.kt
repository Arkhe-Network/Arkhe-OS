package com.cathedral.agi.utils

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint

object Preprocess {
    fun overlayAction(bitmap: Bitmap, action: FloatArray): Bitmap {
        val output = bitmap.copy(Bitmap.Config.ARGB_8888, true)
        val canvas = Canvas(output)
        val paint = Paint().apply { color = android.graphics.Color.WHITE; textSize = 40f }
        canvas.drawText("Action: ${action.joinToString(", ") { "%.2f".format(it) }}", 20f, 100f, paint)
        return output
    }
}