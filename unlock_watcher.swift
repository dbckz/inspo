#!/usr/bin/env swift
/**
 * Screen Unlock Watcher for macOS
 *
 * This helper listens for screen unlock events (including Touch ID)
 * and triggers the inspirational quotes app.
 *
 * Compile with: swiftc -o unlock_watcher unlock_watcher.swift
 */

import Foundation
import Cocoa

// Timestamp formatter
func timestamp() -> String {
    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
    return formatter.string(from: Date())
}

func log(_ message: String) {
    print("[\(timestamp())] \(message)")
    fflush(stdout)  // Ensure immediate output
}

class ScreenUnlockWatcher {
    let scriptPath: String
    var lastTriggerTime: Date = Date.distantPast
    let cooldownSeconds: TimeInterval = 60  // Prevent multiple triggers within 60 seconds

    init(scriptPath: String) {
        self.scriptPath = scriptPath
        setupNotifications()
    }

    func setupNotifications() {
        // Listen for screen unlock notification
        DistributedNotificationCenter.default().addObserver(
            self,
            selector: #selector(screenUnlocked),
            name: NSNotification.Name("com.apple.screenIsUnlocked"),
            object: nil
        )

        // Also listen for screen wake (display wake)
        NSWorkspace.shared.notificationCenter.addObserver(
            self,
            selector: #selector(screenWake),
            name: NSWorkspace.screensDidWakeNotification,
            object: nil
        )

        // Listen for session becoming active (user switched back)
        NSWorkspace.shared.notificationCenter.addObserver(
            self,
            selector: #selector(sessionBecameActive),
            name: NSWorkspace.sessionDidBecomeActiveNotification,
            object: nil
        )

        log("Unlock watcher started. Listening for screen unlock events...")
    }

    @objc func screenUnlocked(_ notification: Notification) {
        triggerQuoteApp(reason: "screen unlock")
    }

    @objc func screenWake(_ notification: Notification) {
        triggerQuoteApp(reason: "screen wake")
    }

    @objc func sessionBecameActive(_ notification: Notification) {
        triggerQuoteApp(reason: "session active")
    }

    func triggerQuoteApp(reason: String) {
        let now = Date()

        // Check cooldown to prevent multiple triggers
        if now.timeIntervalSince(lastTriggerTime) < cooldownSeconds {
            log("Skipping trigger (\(reason)) - cooldown active")
            return
        }

        lastTriggerTime = now
        log("Triggering quote app: \(reason)")

        let task = Process()
        task.launchPath = "/bin/bash"
        task.arguments = [scriptPath]

        do {
            try task.run()
        } catch {
            log("Error launching quote app: \(error)")
        }
    }

    func run() {
        // Keep the app running
        RunLoop.main.run()
    }
}

// Main entry point
let args = CommandLine.arguments
guard args.count > 1 else {
    log("Usage: unlock_watcher <path-to-run-script>")
    exit(1)
}

let scriptPath = args[1]

// Verify the script exists
guard FileManager.default.fileExists(atPath: scriptPath) else {
    log("Error: Script not found at \(scriptPath)")
    exit(1)
}

let watcher = ScreenUnlockWatcher(scriptPath: scriptPath)
watcher.run()
