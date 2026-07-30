// mobile/ios/CathedralEngine.swift
import Foundation

public class CathedralEngine {
    private let handle: UnsafeMutableRawPointer

    public init() {
        handle = cathedral_engine_new()
    }

    deinit {
        cathedral_engine_free(handle)
    }

    public func loadModel(path: String) -> Bool {
        return cathedral_engine_load_model(handle, path)
    }

    public func infer(input: String) -> String? {
        guard let cString = cathedral_engine_infer(handle, input) else {
            return nil
        }
        defer { free(cString) }
        return String(cString: cString)
    }

    public func inferFloat(input: [Float]) -> [Float]? {
        var result = [Float]()
        // ... implementação via JNI/ObjC
        return result
    }

    public func reset() {
        cathedral_engine_reset(handle)
    }
}