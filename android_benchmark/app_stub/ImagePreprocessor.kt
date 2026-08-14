package com.aigc.benchmark

import android.graphics.Bitmap
import java.nio.ByteBuffer

/**
 * Preprocessing skeleton matching pipeline.py's preprocess_jpeg() + transform_infer
 * exactly (see PRODUCTION_ROUTING_SPEC.md ss2). Skeleton only -- not functional code.
 */
object ImagePreprocessor {

    private const val TARGET_SIZE = 224
    private const val JPEG_QUALITY = 85

    /**
     * TODO: re-encode the bitmap as JPEG at JPEG_QUALITY and decode it back,
     * matching pipeline.py's preprocess_jpeg(quality=85). Encoder differences
     * vs. Pillow are expected to cause small, not bit-exact, numeric drift --
     * see PRODUCTION_ROUTING_SPEC.md ss2 note 2.
     */
    fun canonicalizeJpeg(input: Bitmap): Bitmap {
        TODO("Bitmap.compress(JPEG, JPEG_QUALITY) to a stream, then re-decode")
    }

    /**
     * TODO: direct resize (no center crop) to TARGET_SIZE x TARGET_SIZE --
     * both dimensions given explicitly, so this stretches/squashes rather
     * than preserving aspect ratio, matching torchvision.transforms.Resize((224,224)).
     */
    fun resize(input: Bitmap): Bitmap {
        TODO("Bitmap.createScaledBitmap(input, TARGET_SIZE, TARGET_SIZE, filter=true)")
    }

    /**
     * TODO: convert to a NHWC float32 ByteBuffer, RGB channel order, normalized
     * to [-1, 1] via (x/255 - 0.5) / 0.5 -- NOT ImageNet mean/std, per
     * PRODUCTION_ROUTING_SPEC.md ss2/ss5. TFLite interpreter expects NHWC here,
     * NOT NCHW (that distinction only applies at the PyTorch/ONNX boundary).
     */
    fun toNormalizedNHWCBuffer(bitmap: Bitmap): ByteBuffer {
        TODO(
            "Allocate a direct ByteBuffer of size 1*224*224*3*4 bytes (float32), " +
            "iterate pixels row-major, extract R/G/B, apply (x/255f - 0.5f) / 0.5f, " +
            "write in NHWC order"
        )
    }
}
