import QtQuick
import QtQuick.Controls
import QtQuick.Window
import Fkyc 1.0
import "components"
import "pages"

ApplicationWindow {
    id: win
    width: 1440
    height: 1024
    visibility: Window.Maximized
    visible: true
    title: "FKYC"
    color: "#0b1220"
    property string savedNotice: ""

    readonly property real unit: Math.min(width / Theme.frameW, height / Theme.frameH)
    readonly property real ox: (width - Theme.frameW * unit) / 2
    readonly property real oy: (height - Theme.frameH * unit) / 2

    FontLoader { source: assetRoot + "/fonts/SF-Pro-Display-Light.otf" }
    FontLoader { source: assetRoot + "/fonts/SF-Pro-Display-Regular.otf" }
    FontLoader { source: assetRoot + "/fonts/SF-Pro-Display-Medium.otf" }
    FontLoader { source: assetRoot + "/fonts/SF-Pro-Display-Semibold.otf" }
    FontLoader { source: assetRoot + "/fonts/SF-Pro-Display-Bold.otf" }
    FontLoader { source: assetRoot + "/fonts/SF-Pro-Display-Heavy.otf" }
    FontLoader { source: assetRoot + "/fonts/SF-Pro-Display-Black.otf" }

    readonly property real camX0: win.ox + Theme.cardX * win.unit
    readonly property real camY0: win.oy + Theme.cardY * win.unit
    readonly property real camCW: Theme.cardW * win.unit
    readonly property real camCH: Theme.cardH * win.unit
    readonly property real camPad: 32 * win.unit
    readonly property real faceCamW: Theme.faceCamW * win.unit
    readonly property real faceCamH: Theme.faceCamH * win.unit
    readonly property bool ovalScreen: bridge.screen === "face" || bridge.screen === "login" || bridge.screen === "exam"
    readonly property bool loginResultScreen: bridge.screen === "loginResult"
    readonly property bool framedPhotoScreen: bridge.screen === "loginResult" || bridge.screen === "citizenResult" || bridge.screen === "studentResult" || bridge.screen === "faceResult"
    readonly property bool resultScreen: bridge.screen === "loginResult" || bridge.screen === "citizenResult" || bridge.screen === "studentResult" || bridge.screen === "faceResult"
    readonly property real loginPhotoW: Theme.loginPhotoW * win.unit
    readonly property real loginPhotoH: Theme.loginPhotoH * win.unit
    readonly property real cameraX: ovalScreen ? camX0 + (camCW - faceCamW) / 2 : framedPhotoScreen ? camX0 + 36 * win.unit : resultScreen ? camX0 + 28 * win.unit : camX0 + camPad
    readonly property real cameraY: ovalScreen ? camY0 + 48 * win.unit : framedPhotoScreen ? camY0 + 36 * win.unit : resultScreen ? camY0 + 36 * win.unit : camY0 + camPad
    readonly property real cameraW: ovalScreen ? faceCamW : framedPhotoScreen ? loginPhotoW : resultScreen ? camCW * 0.46 : camCW - camPad * 2
    readonly property real cameraH: ovalScreen ? faceCamH : framedPhotoScreen ? loginPhotoH : resultScreen ? camCH - 72 * win.unit : camCH - camPad * 2

    CampusBackground {
        id: campus
        anchors.fill: parent
        z: 0
    }

    GlassPanel {
        id: stageGlass
        z: 1
        x: win.ox + Theme.cardX * win.unit
        y: win.oy + Theme.cardY * win.unit
        width: Theme.cardW * win.unit
        height: Theme.cardH * win.unit
        glassRadius: Theme.radiusGlass * win.unit
        blurSource: campus
    }

    CameraViewport {
        id: cameraViewport
        z: 4
        visible: bridge.screen !== "landing"
        unit: win.unit
        blurSource: campus
        x: win.cameraX
        y: win.cameraY
        width: win.cameraW
        height: win.cameraH
    }

    StackView {
        id: stack
        anchors.fill: parent
        z: 3
        hoverEnabled: false
        initialItem: landingPage
        background: null
        pushEnter: Transition { PauseAnimation { duration: 0 } }
        pushExit: Transition { PauseAnimation { duration: 0 } }
        replaceEnter: Transition { PauseAnimation { duration: 0 } }
        replaceExit: Transition { PauseAnimation { duration: 0 } }
        popEnter: Transition { PauseAnimation { duration: 0 } }
        popExit: Transition { PauseAnimation { duration: 0 } }
    }

    PillButton {
        z: 5
        visible: bridge.screen === "login" || bridge.screen === "citizen" || bridge.screen === "student" || bridge.screen === "face" || bridge.screen === "exam"
        width: 58 * win.unit
        height: 58 * win.unit
        x: win.ox + Theme.cardX * win.unit - 74 * win.unit
        y: win.oy + Theme.cardY * win.unit + Theme.cardH * win.unit / 2 - 29 * win.unit
        frosted: true
        frostFill: 0.18
        blurSource: campus
        label: "‹"
        labelSize: 34 * win.unit
        textFont: "SF Pro Display"
        onClicked: bridge.cancel()
    }

    FlashOverlay {
        z: 6
    }

    Component {
        id: landingPage
        LandingPage {
            notice: win.savedNotice
            unit: win.unit
            ox: win.ox
            oy: win.oy
            blurSource: campus
        }
    }
    Component {
        id: capturePage
        CapturePage { unit: win.unit; ox: win.ox; oy: win.oy; blurSource: campus }
    }
    Component {
        id: resultPage
        ResultPage { unit: win.unit; ox: win.ox; oy: win.oy; blurSource: campus }
    }
    Component {
        id: facePage
        FaceEnrollPage { unit: win.unit; ox: win.ox; oy: win.oy; blurSource: campus }
    }
    Component {
        id: examPage
        ExamPage { unit: win.unit; ox: win.ox; oy: win.oy; blurSource: campus }
    }

    function pageFor(screen) {
        if (screen === "landing")
            return landingPage
        if (screen === "face")
            return facePage
        if (screen === "exam")
            return examPage
        if (screen === "loginResult" || screen === "citizenResult" || screen === "studentResult" || screen === "faceResult")
            return resultPage
        return capturePage
    }

    Connections {
        target: bridge
        function onScreenChanged() {
            stack.replace(stack.currentItem, pageFor(bridge.screen), {}, StackView.Immediate)
        }
        function onSaved(userId) {
            win.savedNotice = "Saved profile " + userId
        }
        function onNotice(text) {
            win.savedNotice = text
        }
    }
}
