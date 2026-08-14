// ImagePreprocessor.swift
//
// STATUS: skeleton only, prepared on Windows -- never compiled, never run.
// Must exactly replicate pipeline.py's preprocess_jpeg() + transform_infer.
// See ../IOS_BENCHMARK_SPEC.md section 2 for the authoritative spec this
// was transcribed from -- if this file and the spec ever disagree, the
// Python source (pipeline.py) wins, not this file.

import Foundation
import UIKit
// TODO: add `import TensorFlowLite` (or the CoreML equivalent, see
// IOS_BENCHMARK_SPEC.md's CoreML-vs-LiteRT TODO) once the dependency is
// added via SPM/CocoaPods on the Mac.

enum ImagePreprocessor {

    /// Step 1 of pipeline.py's preprocessing: re-encode as JPEG q=85, then
    /// decode back to a bitmap. Matches `preprocess_jpeg()` in pipeline.py.
    ///
    /// TODO (see IOS_BENCHMARK_SPEC.md section 2, item 2): confirm that
    /// UIImage's jpegData(compressionQuality:) quality scale lines up with
    /// Pillow's JPEG quality=85. These are NOT guaranteed to be the same
    /// encoder or the same quality curve -- do not assume bit-exact
    /// equivalence, just "close enough for a face-classification model."
    static func jpegCanonicalize(_ image: UIImage, quality: CGFloat = 0.85) -> UIImage? {
        guard let data = image.jpegData(compressionQuality: quality) else { return nil }
        return UIImage(data: data)
    }

    /// Step 2: direct resize to 224x224 (NOT aspect-preserving, NOT
    /// center-cropped -- pipeline.py uses `transforms.Resize((224,224))`
    /// which stretches to the exact target size). TODO: implement with
    /// CoreGraphics/UIGraphicsImageRenderer once on the Mac.
    static func resize224(_ image: UIImage) -> UIImage? {
        // TODO: implement. Must NOT preserve aspect ratio -- direct squash
        // to 224x224, matching torchvision's Resize((224,224)) behavior.
        fatalError("TODO: implement resize224 on the Mac")
    }

    /// Steps 3-5: convert to a normalized float32 tensor.
    ///   - RGB channel order (not BGR)
    ///   - [0,1] scale via ToTensor-equivalent, then (x-0.5)/0.5 -> [-1,1]
    ///   - Output layout: NHWC (channels-last), per IOS_BENCHMARK_SPEC.md
    ///     section 2 item 7 -- the exported .tflite models expect NHWC,
    ///     NOT the NCHW layout PyTorch/ONNX used internally. Getting this
    ///     wrong will not crash, it will silently produce garbage
    ///     predictions -- verify against a known-good image / known
    ///     prediction before trusting any benchmark numbers.
    ///
    /// Returns a flat [Float] of length 1*224*224*3 in NHWC order, or nil
    /// on failure.
    static func toNormalizedNHWCTensor(_ image: UIImage) -> [Float]? {
        // TODO: implement. Suggested approach: draw into a CVPixelBuffer
        // or raw RGBA8 bitmap context, then walk pixels row-major producing
        // NHWC float32 in [-1,1] per channel (R,G,B; no alpha).
        fatalError("TODO: implement toNormalizedNHWCTensor on the Mac")
    }

    /// Convenience: full pipeline from a UIImage to a model-ready tensor,
    /// chaining jpegCanonicalize -> resize224 -> toNormalizedNHWCTensor.
    /// Mirrors pipeline.py's run_single() preprocessing order exactly.
    static func preprocess(_ image: UIImage) -> [Float]? {
        guard let canonical = jpegCanonicalize(image),
              let resized = resize224(canonical) else {
            return nil
        }
        return toNormalizedNHWCTensor(resized)
    }
}
