import QtQuick
import Fkyc 1.0

// Viền oval được vẽ trên CameraViewport. File này giữ chỗ cho lớp progress
// khi cần tách khỏi viewport. Không dùng Rectangle để khoét lỗ.
Item {
    property real progress: bridge.progress
    property string tone: bridge.ovalColor
}
