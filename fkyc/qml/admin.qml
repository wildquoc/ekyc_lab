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
    title: "ADMIN"
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
    readonly property real faceCamW: Theme.faceCamW * win.unit
    readonly property real faceCamH: Theme.faceCamH * win.unit
    readonly property real cameraX: camX0 + (camCW - faceCamW) / 2
    readonly property real cameraY: camY0 + (48 + Theme.loginCamDrop) * win.unit
    readonly property real cameraW: faceCamW
    readonly property real cameraH: faceCamH

    CampusBackground {
        id: campus
        anchors.fill: parent
        z: 0
    }

    GlassPanel {
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
        visible: bridge.screen === "login"
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
        visible: bridge.screen === "login" || bridge.screen === "manualLogin" || bridge.screen === "users"
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

    FlashOverlay { z: 6 }

    Component {
        id: landingPage
        LandingPage {
            notice: win.savedNotice
            brand: "ADMIN"
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
        id: manualPage
        ManualLoginPage { unit: win.unit; ox: win.ox; oy: win.oy; blurSource: campus }
    }
    Component {
        id: usersPage
        UsersPage { unit: win.unit; ox: win.ox; oy: win.oy; blurSource: campus }
    }

    function pageFor(screen) {
        if (screen === "manualLogin")
            return manualPage
        if (screen === "login")
            return capturePage
        if (screen === "users")
            return usersPage
        return landingPage
    }

    Connections {
        target: bridge
        function onScreenChanged() {
            if (bridge.screen === "welcome" || bridge.screen === "loginResult") {
                bridge.enterAdmin()
                return
            }
            stack.replace(stack.currentItem, pageFor(bridge.screen), {}, StackView.Immediate)
        }
        function onNotice(text) {
            win.savedNotice = text
        }
    }
}
