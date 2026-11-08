import QtQuick
import QtQuick.Controls
import Fkyc 1.0
import "../components"

Item {
    id: page
    property real unit: 1
    property real ox: 0
    property real oy: 0
    property Item blurSource: null

    readonly property real formW: 460 * page.unit
    readonly property real formX: page.ox + (Theme.cardX + (Theme.cardW - 460) / 2) * page.unit

    Text {
        x: page.formX
        y: page.oy + (Theme.cardY + 210) * page.unit
        width: page.formW
        text: "Log in manually"
        color: "#ffffff"
        horizontalAlignment: Text.AlignHCenter
        font.family: "SF Pro Display"
        font.pixelSize: 36 * page.unit
        font.weight: Font.Bold
    }

    component EntryBox: FocusScope {
        id: box
        property string hint: ""
        property int echo: TextInput.Normal
        property alias text: input.text
        signal accepted()
        function edit() {
            input.forceActiveFocus()
        }

        Rectangle {
            anchors.fill: parent
            radius: height / 2
            color: Qt.rgba(1, 1, 1, 0.16)
            border.width: 1
            border.color: input.activeFocus ? Qt.rgba(1, 1, 1, 0.72) : Qt.rgba(1, 1, 1, 0.38)

            Text {
                x: 28 * page.unit
                anchors.verticalCenter: parent.verticalCenter
                visible: input.text.length === 0
                text: box.hint
                color: Qt.rgba(1, 1, 1, 0.55)
                font.family: "SF Pro Display"
                font.pixelSize: 22 * page.unit
                font.weight: Font.Medium
            }

            TextInput {
                id: input
                property bool caretOn: true
                anchors.fill: parent
                anchors.leftMargin: 28 * page.unit
                anchors.rightMargin: 28 * page.unit
                verticalAlignment: TextInput.AlignVCenter
                horizontalAlignment: TextInput.AlignLeft
                color: "#ffffff"
                selectionColor: Qt.rgba(1, 1, 1, 0.28)
                selectedTextColor: "#ffffff"
                font.family: "SF Pro Display"
                font.pixelSize: 22 * page.unit
                clip: true
                selectByMouse: true
                echoMode: box.echo
                cursorVisible: activeFocus
                cursorDelegate: Item {
                    width: Math.max(2, 2 * page.unit)
                    Rectangle {
                        anchors.fill: parent
                        color: "#ffffff"
                        radius: 1
                        opacity: input.activeFocus && input.caretOn ? 1 : 0
                    }
                }
                onActiveFocusChanged: if (activeFocus) caretOn = true
                onAccepted: box.accepted()

                Timer {
                    interval: 530
                    repeat: true
                    running: input.activeFocus
                    onTriggered: input.caretOn = !input.caretOn
                }
            }
        }
    }

    EntryBox {
        id: userField
        x: page.formX
        y: page.oy + (Theme.cardY + 300) * page.unit
        width: page.formW
        height: 64 * page.unit
        hint: "Username"
        onAccepted: passField.edit()
    }

    EntryBox {
        id: passField
        x: page.formX
        y: page.oy + (Theme.cardY + 384) * page.unit
        width: page.formW
        height: 64 * page.unit
        hint: "Password"
        echo: TextInput.Password
        onAccepted: page.submit()
    }

    Text {
        x: page.formX
        y: page.oy + (Theme.cardY + 460) * page.unit
        width: page.formW
        visible: bridge.errorText !== ""
        text: bridge.errorText
        color: "#ffd0d0"
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        font.family: "SF Pro Display"
        font.pixelSize: 16 * page.unit
        font.weight: Font.Medium
    }

    PillButton {
        x: page.formX + (page.formW - 220 * page.unit) / 2
        y: page.oy + (Theme.cardY + 510) * page.unit
        width: 220 * page.unit
        height: 64 * page.unit
        frosted: true
        blurSource: page.blurSource
        label: "Log in"
        labelSize: 24 * page.unit
        textFont: "SF Pro Display"
        onClicked: page.submit()
    }

    function submit() {
        bridge.submitManual(userField.text, passField.text)
    }
}
