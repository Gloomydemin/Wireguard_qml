// ImportPage.qml
import QtQuick 2.0
import Lomiri.Components 1.3 as UITK
import Lomiri.Content 1.3 as ContentHub

UITK.Page {
    id: importPage
    
    property int contentType: ContentHub.ContentType.Documents
    property int handler: ContentHub.ContentHandler.Source
    
    signal importFinished(string filePath)
    signal importCancelled()
    
    header: UITK.PageHeader {
        id: pageHeader
        title: i18n.tr("Select File")
        trailingActionBar.actions: [
            UITK.Action {
                iconName: "close"
                onTriggered: {
                    importCancelled()
                    pageStack.pop()
                }
            }
        ]
    }
    
    ContentHub.ContentPeerPicker {
        id: picker
        anchors {
            fill: parent
            topMargin: pageHeader.height
        }
        visible: true
        showTitle: false
        contentType: importPage.contentType
        handler: importPage.handler
        
        onPeerSelected: {
            console.log("Peer selected:", peer)
            
            if (!peer) {
                console.log("No peer selected")
                importCancelled()
                pageStack.pop()
                return
            }
            
            // Create closure to keep context
            var selectedPeer = peer
            selectedPeer.selectionType = ContentHub.ContentTransfer.Single
            var transfer = selectedPeer.request()
            
            if (!transfer) {
                console.log("Failed to create transfer")
                importCancelled()
                pageStack.pop()
                return
            }
            
            console.log("Transfer created, state:", transfer.state)
            
            if (transfer.state === ContentHub.ContentTransfer.Charged) {
                processTransfer(transfer)
            } else {
                // Subscribe to state change
                var stateChangedHandler = function() {
                    console.log("Transfer state changed:", transfer.state)
                    if (transfer.state === ContentHub.ContentTransfer.Charged) {
                        processTransfer(transfer)
                        transfer.stateChanged.disconnect(stateChangedHandler)
                    } else if (transfer.state === ContentHub.ContentTransfer.Failed) {
                        console.log("Transfer failed")
                        importCancelled()
                        pageStack.pop()
                        transfer.stateChanged.disconnect(stateChangedHandler)
                    }
                }
                transfer.stateChanged.connect(stateChangedHandler)
            }
        }
        
        onCancelPressed: {
            console.log("Import cancelled by user")
            importCancelled()
            pageStack.pop()
        }
    }
    
    function processTransfer(transfer) {
        console.log("Processing transfer, items count:", transfer.items ? transfer.items.length : 0)
        
        if (!transfer.items || transfer.items.length === 0) {
            console.log("No items in transfer")
            importCancelled()
            pageStack.pop()
            return
        }
        
        var fileItem = transfer.items[0]
        if (!fileItem || !fileItem.url) {
            console.log("Invalid file item")
            importCancelled()
            pageStack.pop()
            return
        }
        
        var fileUrl = fileItem.url
        console.log("File URL:", fileUrl)
        
        // Convert URL to path
        var filePath = fileUrl.toString()
        
        // Remove file:// prefix if present
        if (filePath.startsWith("file://")) {
            filePath = filePath.substring(7)
        }
        
        console.log("Final file path:", filePath)
        
        // Emit signal first, then return
        importFinished(filePath)
        
        // Small delay so signal is processed before pop
        Qt.callLater(function() {
            pageStack.pop()
        })
    }
    
    Component.onCompleted: {
        console.log("ImportPage created with contentType:", contentType, "handler:", handler)
    }
    
    Component.onDestruction: {
        console.log("ImportPage destroyed")
    }
}
