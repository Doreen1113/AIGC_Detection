// HierarchicalRouter.swift
//
// STATUS: skeleton only, prepared on Windows -- never compiled, never run.
// Implements the Layer1 -> Layer2 routing decision. See
// ../IOS_BENCHMARK_SPEC.md section 4 for the two candidate rules (exact
// production composite-probability rule vs. the desktop benchmark's
// strict-gate approximation) and the open TODO on which one this harness
// should implement -- that decision is NOT made in this file, resolve it
// on the Mac before trusting any "real path" vs "manipulated path" latency
// split.

import Foundation

enum Prediction: String {
    case real
    case fake
    case filter
}

struct RoutingResult {
    let prediction: Prediction
    let pReal: Float
    let pFake: Float
    let pFilter: Float
    /// Whether Layer2 was actually invoked for this image (matters for the
    /// latency accounting -- see IOS_BENCHMARK_SPEC.md section 4).
    let layer2Invoked: Bool
}

enum HierarchicalRouter {

    private static func softmax(_ logits: [Float]) -> [Float] {
        let maxVal = logits.max() ?? 0
        let exps = logits.map { expf($0 - maxVal) }
        let sum = exps.reduce(0, +)
        return exps.map { $0 / sum }
    }

    /// Layer1 classes: index 0 = real, index 1 = manipulated.
    /// Layer2 classes: index 0 = fake, index 1 = filter.
    /// See IOS_BENCHMARK_SPEC.md section 3-4 for the source of this
    /// convention (pipeline.py's CLASSES + hierarchical_predict()).

    /// TODO: pick ONE of these two rules and delete the other before this
    /// ships -- keeping both here only so the choice is visible and
    /// deliberate, not because the app should support switching at runtime.

    /// Rule A -- exact production rule (pipeline.py hierarchical_predict).
    /// Layer2 ALWAYS runs; final prediction is the argmax of a composite
    /// 3-way probability, not a hard gate on Layer1 alone.
    static func routeProductionRule(l1Logits: [Float], l2Logits: [Float]) -> RoutingResult {
        let p1 = softmax(l1Logits)
        let pReal = p1[0]
        let pManip = p1[1]

        let p2 = softmax(l2Logits)
        let pFakeGivenManip = p2[0]
        let pFilterGivenManip = p2[1]

        let pFake = pManip * pFakeGivenManip
        let pFilter = pManip * pFilterGivenManip

        let candidates: [(Prediction, Float)] = [(.real, pReal), (.fake, pFake), (.filter, pFilter)]
        let winner = candidates.max(by: { $0.1 < $1.1 })!

        return RoutingResult(prediction: winner.0, pReal: pReal, pFake: pFake, pFilter: pFilter, layer2Invoked: true)
    }

    /// Rule B -- strict-gate approximation (benchmark_mobile_artifacts.py's
    /// hierarchical()). Layer2 is only invoked when Layer1's argmax is
    /// "manipulated" -- cheaper for confident-real images. This is the rule
    /// the desktop reference numbers in benchmark_manifest.json were
    /// measured under.
    ///
    /// `l2LogitsProvider` is a closure so Layer2 inference is genuinely
    /// skipped (not computed-then-ignored) when Layer1 says real --
    /// otherwise the "real path" latency measurement in
    /// BENCHMARK_ACCEPTANCE_GATE.md would be wrong.
    static func routeStrictGateRule(l1Logits: [Float], l2LogitsProvider: () -> [Float]) -> RoutingResult {
        let p1 = softmax(l1Logits)
        let pReal = p1[0]
        let pManip = p1[1]

        if pReal >= pManip {
            return RoutingResult(prediction: .real, pReal: pReal, pFake: 0, pFilter: 0, layer2Invoked: false)
        }

        let l2Logits = l2LogitsProvider()
        let p2 = softmax(l2Logits)
        let prediction: Prediction = p2[0] >= p2[1] ? .fake : .filter
        return RoutingResult(prediction: prediction, pReal: pReal, pFake: p2[0], pFilter: p2[1], layer2Invoked: true)
    }
}
