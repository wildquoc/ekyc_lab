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

    readonly property real pad: 48 * page.unit
    readonly property real x0: page.ox + Theme.cardX * page.unit + page.pad
    readonly property real y0: page.oy + Theme.cardY * page.unit + page.pad
    readonly property real innerW: Theme.cardW * page.unit - page.pad * 2
    readonly property real innerH: Theme.cardH * page.unit - page.pad * 2

    property bool formOpen: false
    property string originalName: ""
    property string formError: ""
    property string askAction: ""
    property string askUser: ""
    signal confirmRequested()

    function openAsk(action, user) {
        page.askUser = user
        page.askAction = action
        page.confirmRequested()
    }

    ListModel { id: users }

    function reload() {
        users.clear()
        var rows = JSON.parse(bridge.accountList())
        for (var i = 0; i < rows.length; i++)
            users.append(rows[i])
    }

    function openAdd() {
        page.originalName = ""
        page.formError = ""
        page.askAction = ""
        userField.text = ""
        passField.text = ""
        page.formOpen = true
        userField.edit()
    }

    function openEdit(username, password) {
        page.originalName = username
        page.formError = ""
        page.askAction = ""
        userField.text = username
        passField.text = password
        page.formOpen = true
        userField.edit()
    }

    function closeForm() {
        page.formOpen = false
        page.formError = ""
        page.askAction = ""
    }

    function acceptAsk() {
        var err = ""
        if (page.askAction === "delete")
            err = bridge.deleteAccount(page.askUser)
        else if (page.askAction === "erase")
            err = bridge.eraseFace(page.askUser)
        page.askAction = ""
        page.askUser = ""
        if (err) {
            page.formError = err
            return
        }
        page.formError = ""
        page.reload()
    }

    Component.onCompleted: reload()

    Item {
        id: sheet
        anchors.fill: parent

    Text {
        x: page.x0
        y: page.y0
        width: page.innerW * 0.6
        text: page.formOpen ? (page.originalName === "" ? "Add user" : "Edit user") : "Users"
        color: "#ffffff"
        font.family: "SF Pro Display"
        font.pixelSize: 40 * page.unit
        font.weight: Font.Bold
    }

    PillButton {
        visible: !page.formOpen
        x: page.x0 + page.innerW - 180 * page.unit
        y: page.y0
        width: 180 * page.unit
        height: 52 * page.unit
        frosted: true
        blurSource: page.blurSource
        label: "Add"
        labelSize: 22 * page.unit
        textFont: "SF Pro Display"
        onClicked: page.openAdd()
    }

    Flickable {
        id: list
        visible: !page.formOpen
        x: page.x0
        y: page.y0 + 76 * page.unit
        width: page.innerW
        height: page.innerH - 76 * page.unit
        contentHeight: column.height
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: column
            width: list.width
            spacing: 12 * page.unit

            Repeater {
                model: users
                delegate: Rectangle {
                    required property string username
                    required property string password
                    required property bool faceReady
                    width: column.width
                    height: 72 * page.unit
                    radius: height / 2
                    color: Qt.rgba(1, 1, 1, 0.12)
                    border.width: 1
                    border.color: Qt.rgba(1, 1, 1, 0.28)

                    Text {
                        x: 28 * page.unit
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width * 0.26
                        text: username
                        color: "#ffffff"
                        elide: Text.ElideRight
                        font.family: "SF Pro Display"
                        font.pixelSize: 22 * page.unit
                        font.weight: Font.Bold
                    }

                    Text {
                        x: parent.width * 0.30
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width * 0.16
                        text: password
                        color: Qt.rgba(1, 1, 1, 0.72)
                        elide: Text.ElideRight
                        font.family: "SF Pro Display"
                        font.pixelSize: 20 * page.unit
                    }

                    Rectangle {
                        anchors.right: editButton.left
                        anchors.rightMargin: 12 * page.unit
                        anchors.verticalCenter: parent.verticalCenter
                        width: 168 * page.unit
                        height: 40 * page.unit
                        radius: height / 2
                        color: faceReady ? "#10b981" : "transparent"
                        border.width: faceReady ? 0 : 1
                        border.color: Qt.rgba(1, 1, 1, 0.4)

                        Text {
                            anchors.centerIn: parent
                            text: faceReady ? "FaceID" : "Not Registered"
                            color: "#ffffff"
                            font.family: "SF Pro Display"
                            font.pixelSize: 15 * page.unit
                            font.weight: Font.Bold
                        }
                    }

                    PillButton {
                        id: editButton
                        anchors.right: delButton.left
                        anchors.rightMargin: 10 * page.unit
                        anchors.verticalCenter: parent.verticalCenter
                        width: 110 * page.unit
                        height: 44 * page.unit
                        frosted: true
                        blurSource: page.blurSource
                        label: "Edit"
                        labelSize: 18 * page.unit
                        textFont: "SF Pro Display"
                        onClicked: page.openEdit(username, password)
                    }

                    PillButton {
                        id: delButton
                        anchors.right: parent.right
                        anchors.rightMargin: 14 * page.unit
                        anchors.verticalCenter: parent.verticalCenter
                        width: 120 * page.unit
                        height: 44 * page.unit
                        frosted: true
                        blurSource: page.blurSource
                        label: "Delete"
                        labelSize: 18 * page.unit
                        textFont: "SF Pro Display"
                        onClicked: {
                            page.formError = ""
                            page.openAsk("delete", username)
                        }
                    }
                }
            }
        }
    }

    Text {
        visible: !page.formOpen && page.formError !== ""
        x: page.x0
        y: page.y0 + page.innerH - 28 * page.unit
        width: page.innerW
        text: page.formError
        color: "#ffffff"
        horizontalAlignment: Text.AlignHCenter
        font.family: "SF Pro Display"
        font.pixelSize: 18 * page.unit
    }

    component EntryBox: FocusScope {
        id: box
        property string hint: ""
        property int echo: TextInput.Normal
        property alias text: input.text
        function edit() { input.forceActiveFocus() }

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
            }

            TextInput {
                id: input
                property bool caretOn: true
                anchors.fill: parent
                anchors.leftMargin: 28 * page.unit
                anchors.rightMargin: 28 * page.unit
                verticalAlignment: TextInput.AlignVCenter
                color: "#ffffff"
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
                        opacity: input.activeFocus && input.caretOn ? 1 : 0
                    }
                }
            }
        }

        Timer {
            interval: 530
            running: input.activeFocus
            repeat: true
            onTriggered: input.caretOn = !input.caretOn
        }
    }

    EntryBox {
        id: userField
        visible: page.formOpen
        x: page.x0 + (page.innerW - width) / 2
        y: page.y0 + 140 * page.unit
        width: 460 * page.unit
        height: 64 * page.unit
        hint: "Username"
    }

    EntryBox {
        id: passField
        visible: page.formOpen
        x: userField.x
        y: userField.y + 84 * page.unit
        width: userField.width
        height: userField.height
        hint: "Password"
    }

    PillButton {
        id: eraseButton
        visible: page.formOpen && page.originalName !== ""
        x: userField.x
        y: passField.y + 84 * page.unit
        width: userField.width
        height: 56 * page.unit
        frosted: true
        blurSource: page.blurSource
        label: "Erase FaceID"
        labelSize: 22 * page.unit
        textFont: "SF Pro Display"
        onClicked: {
            page.formError = ""
            page.openAsk("erase", page.originalName)
        }
    }

    Text {
        visible: page.formOpen && page.formError !== ""
        x: userField.x
        y: (page.originalName !== "" ? eraseButton.y + eraseButton.height + 12 * page.unit : passField.y + 80 * page.unit)
        width: userField.width
        text: page.formError
        color: "#ffffff"
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        font.family: "SF Pro Display"
        font.pixelSize: 18 * page.unit
    }

    PillButton {
        visible: page.formOpen
        x: userField.x
        y: passField.y + (page.originalName !== "" ? 210 : 130) * page.unit
        width: (userField.width - 16 * page.unit) / 2
        height: 56 * page.unit
        frosted: true
        blurSource: page.blurSource
        label: "Save"
        labelSize: 22 * page.unit
        textFont: "SF Pro Display"
        onClicked: {
            var err = bridge.saveAccount(page.originalName, userField.text, passField.text)
            if (err) {
                page.formError = err
                return
            }
            page.closeForm()
            page.reload()
        }
    }

    PillButton {
        visible: page.formOpen
        x: userField.x + (userField.width + 16 * page.unit) / 2
        y: passField.y + (page.originalName !== "" ? 210 : 130) * page.unit
        width: (userField.width - 16 * page.unit) / 2
        height: 56 * page.unit
        frosted: true
        blurSource: page.blurSource
        label: "Cancel"
        labelSize: 22 * page.unit
        textFont: "SF Pro Display"
        onClicked: page.closeForm()
    }

    }
}
