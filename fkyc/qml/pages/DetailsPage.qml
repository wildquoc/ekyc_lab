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

    component EntryBox: FocusScope {
        id: box
        property string hint: ""
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

    Text {
        x: page.formX
        y: page.oy + (Theme.cardY + 150) * page.unit
        width: page.formW
        text: "Enter your details"
        color: "#ffffff"
        horizontalAlignment: Text.AlignHCenter
        font.family: "SF Pro Display"
        font.pixelSize: 36 * page.unit
        font.weight: Font.Bold
    }

    EntryBox {
        id: dobField
        x: page.formX
        y: page.oy + (Theme.cardY + 240) * page.unit
        width: page.formW
        height: 64 * page.unit
        hint: "Date of Birth"
        onAccepted: idField.edit()
    }

    EntryBox {
        id: idField
        x: page.formX
        y: page.oy + (Theme.cardY + 320) * page.unit
        width: page.formW
        height: 64 * page.unit
        hint: "Citizen ID"
        onAccepted: nameField.edit()
    }

    EntryBox {
        id: nameField
        x: page.formX
        y: page.oy + (Theme.cardY + 400) * page.unit
        width: page.formW
        height: 64 * page.unit
        hint: "Name"
        onAccepted: studentField.edit()
    }

    EntryBox {
        id: studentField
        x: page.formX
        y: page.oy + (Theme.cardY + 480) * page.unit
        width: page.formW
        height: 64 * page.unit
        hint: "Student ID"
        onAccepted: page.submit()
    }

    Text {
        x: page.formX
        y: page.oy + (Theme.cardY + 556) * page.unit
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
        y: page.oy + (Theme.cardY + 600) * page.unit
        width: 220 * page.unit
        height: 64 * page.unit
        frosted: true
        blurSource: page.blurSource
        label: "Save"
        labelSize: 24 * page.unit
        textFont: "SF Pro Display"
        onClicked: page.submit()
    }

    function submit() {
        bridge.submitDetails(dobField.text, idField.text, nameField.text, studentField.text)
    }
}
