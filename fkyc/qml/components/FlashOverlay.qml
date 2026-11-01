import QtQuick
import QtQuick.Shapes
import Fkyc 1.0

// Lỗ oval: Shape + OddEvenFill. Rectangle không khoét được lỗ lõm.
Shape {
    id: flash
    anchors.fill: parent
    visible: bridge.flashActive
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
        fillRule: ShapePath.OddEvenFill
        strokeWidth: -1
        fillColor: bridge.flashColor
        PathRectangle {
            x: 0
            y: 0
            width: flash.width
            height: flash.height
        }
        // Qt 6.12 không đăng ký type PathEllipse. Hai cung SVG vẫn là subpath
        // ellipse trong cùng ShapePath OddEvenFill, nên vùng mặt bị đục lỗ.
        PathSvg {
            path: {
                var rx = Math.max(1, bridge.ovalWidth / 2)
                var ry = Math.max(1, bridge.ovalHeight / 2)
                var cx = bridge.ovalX + rx
                var cy = bridge.ovalY + ry
                return "M " + (cx - rx) + " " + cy
                    + " A " + rx + " " + ry + " 0 1 0 " + (cx + rx) + " " + cy
                    + " A " + rx + " " + ry + " 0 1 0 " + (cx - rx) + " " + cy
                    + " Z"
            }
        }
    }
}
