import QtQuick
import QtQuick.Controls
import QtQuick.Window
import Qt5Compat.GraphicalEffects
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

    Item {
        id: world
        anchors.fill: parent

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

    }

    Item {
        id: confirm
        z: 40
        visible: false
        anchors.fill: parent

        function open() { confirm.visible = true }
        function close() { confirm.visible = false }
        function accept() {
            var page = stack.currentItem
            confirm.close()
            if (page && page.acceptAsk)
                page.acceptAsk()
        }
        function dismiss() {
            var page = stack.currentItem
            if (page) {
                page.askAction = ""
                page.askUser = ""
            }
            confirm.close()
        }

        readonly property real boxW: 460 * win.unit
        readonly property real boxH: 230 * win.unit
        readonly property real blurPad: 72

        ShaderEffectSource {
            id: sceneGrab
            visible: false
            live: confirm.visible
            hideSource: false
            smooth: true
            width: askCard.width + confirm.blurPad * 2
            height: askCard.height + confirm.blurPad * 2
            sourceItem: world
            sourceRect: {
                var origin = askCard.mapToItem(world, -confirm.blurPad, -confirm.blurPad)
                return Qt.rect(origin.x, origin.y, askCard.width + confirm.blurPad * 2, askCard.height + confirm.blurPad * 2)
            }
        }

        Item {
            id: askCard
            width: confirm.boxW
            height: confirm.boxH
            x: win.ox + (Theme.cardX + Theme.cardW / 2) * win.unit - width / 2
            y: win.oy + (Theme.cardY + Theme.cardH / 2) * win.unit - height / 2

            Item {
                id: blurPlate
                anchors.fill: parent
                clip: true
                visible: false
                layer.enabled: true

                FastBlur {
                    x: -confirm.blurPad
                    y: -confirm.blurPad
                    width: askCard.width + confirm.blurPad * 2
                    height: askCard.height + confirm.blurPad * 2
                    source: sceneGrab
                    radius: 64
                    transparentBorder: false
                }
            }

            Rectangle {
                id: roundMask
                anchors.fill: parent
                radius: 32 * win.unit
                visible: false
                layer.enabled: true
            }

            OpacityMask {
                anchors.fill: parent
                source: blurPlate
                maskSource: roundMask
            }

            Rectangle {
                anchors.fill: parent
                radius: 32 * win.unit
                color: "transparent"
                border.width: 1
                border.color: Qt.rgba(1, 1, 1, 0.55)
            }

            MouseArea { anchors.fill: parent }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 52 * win.unit
                text: "Are you sure?"
                color: "#ffffff"
                font.family: "SF Pro Display"
                font.pixelSize: 32 * win.unit
                font.weight: Font.Bold
            }

            PillButton {
                x: 36 * win.unit
                y: parent.height - 84 * win.unit
                width: (parent.width - 88 * win.unit) / 2
                height: 52 * win.unit
                frosted: true
                blurSource: campus
                label: "Yes"
                labelSize: 22 * win.unit
                textFont: "SF Pro Display"
                onClicked: confirm.accept()
            }

            PillButton {
                x: parent.width / 2 + 8 * win.unit
                y: parent.height - 84 * win.unit
                width: (parent.width - 88 * win.unit) / 2
                height: 52 * win.unit
                frosted: true
                blurSource: campus
                label: "Cancel"
                labelSize: 22 * win.unit
                textFont: "SF Pro Display"
                onClicked: confirm.dismiss()
            }
        }
    }

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
        UsersPage {
            unit: win.unit
            ox: win.ox
            oy: win.oy
            blurSource: campus
            onConfirmRequested: confirm.open()
            onAskActionChanged: {
                if (askAction === "")
                    confirm.close()
            }
        }
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
            confirm.close()
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
