// Text and its place on a picture, from macOS's own Vision. Prints JSON: [{"text","x","y","w","h"}], all 0 to 1, top left origin. Free and on this machine: nothing leaves it.
import Foundation
import Vision
import ImageIO
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let src = CGImageSourceCreateWithURL(url as CFURL, nil), let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { print("[]"); exit(0) }
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
var out: [[String: Any]] = []
for r in req.results ?? [] { guard let c = r.topCandidates(1).first else { continue }; let b = r.boundingBox; out.append(["text": c.string, "x": b.minX, "y": 1 - b.maxY, "w": b.width, "h": b.height]) }
print(String(data: try! JSONSerialization.data(withJSONObject: out), encoding: .utf8)!)
