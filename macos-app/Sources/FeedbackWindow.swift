import Cocoa

/// Menu entry point and app-lifetime chores for feedback; keeps AppDelegate untouched
/// except for one menu line. `start()` is called once from main.swift.
final class FeedbackCenter: NSObject {
    static let shared = FeedbackCenter()
    private var controller: FeedbackWindowController?
    private var retryTimer: Timer?

    /// Uptime clock, local retention (utility queue), retry queue: 10 s after launch, then hourly.
    func start() {
        Diagnostics.launchDate = Date()
        DispatchQueue.global(qos: .utility).async { FeedbackStore.applyRetention() }
        let timer = Timer(fire: Date().addingTimeInterval(10), interval: 3600, repeats: true) { _ in
            FeedbackDelivery.retryPending()
        }
        RunLoop.main.add(timer, forMode: .common)
        retryTimer = timer
    }

    /// «Написать отзыв…» for the status-bar menu.
    func menuItem() -> NSMenuItem {
        let item = NSMenuItem(title: FBText.menuItem, action: #selector(openFeedback), keyEquivalent: "")
        item.target = self
        return item
    }

    /// Single instance: brings the existing window to the front.
    @objc func openFeedback() {
        if controller == nil {
            let c = FeedbackWindowController(config: FeedbackConfig.load())
            c.onClose = { [weak self] in
                DispatchQueue.main.async { self?.controller = nil }
            }
            controller = c
        }
        controller?.present()
    }
}

/// The feedback form: a normal titled window (never on the wallpaper level). Nothing leaves
/// the Mac until «Отправить» with consent; a local copy is always written first.
final class FeedbackWindowController: NSWindowController, NSWindowDelegate, NSTextViewDelegate, NSTextFieldDelegate {
    var onClose: (() -> Void)?

    private static let rowWidth: CGFloat = 440
    private static let autosaveName = "AQFeedback"
    private let config: FeedbackConfig

    // Form (scrolls)
    private let formScroll = NSScrollView()
    private let formDoc = FlippedView(frame: NSRect(x: 0, y: 0, width: 480, height: 600))
    private let form = NSStackView()
    private let categoryControl = NSSegmentedControl(labels: FBText.categories, trackingMode: .selectOne,
                                                     target: nil, action: nil)
    private let fishGroup = NSStackView()
    private let fishField = NSTextField(string: "")
    private let messageScroll: NSScrollView
    private let messageView: NSTextView
    private let messagePlaceholder = PassthroughLabel(labelWithString: FBText.messagePlaceholder)
    private let counterLabel = NSTextField(labelWithString: "")
    private let emailField = NSTextField(string: "")
    private let emailError = NSTextField(labelWithString: FBText.emailError)
    private let marketingBox = NSButton(checkboxWithTitle: "", target: nil, action: nil)
    private let marketingLabel = NSTextField(wrappingLabelWithString: FBText.marketing)
    private let snapshotBox = NSButton(checkboxWithTitle: FBText.snapshotToggle, target: nil, action: nil)
    private let snapshotThumb = NSImageView()
    private let snapshotCaption = NSTextField(wrappingLabelWithString: "")
    private let diagBox = NSButton(checkboxWithTitle: FBText.diagToggle, target: nil, action: nil)
    private let diagDisclosure = NSButton(title: "", target: nil, action: nil)
    private let diagScroll: NSScrollView
    private let diagText: NSTextView

    // Footer (always visible)
    private let consentBox = NSButton(checkboxWithTitle: "", target: nil, action: nil)
    private let consentLabel = NSTextField(wrappingLabelWithString: FBText.consent)
    private let privacyButton = NSButton(title: "", target: nil, action: nil)
    private let routeLabel = NSTextField(wrappingLabelWithString: "")
    private let statusLabel = NSTextField(wrappingLabelWithString: "")
    private let progress = NSProgressIndicator()
    private let progressLabel = NSTextField(labelWithString: FBText.sending)
    private let cancelButton = NSButton(title: FBText.cancel, target: nil, action: nil)
    private let sendButton = NSButton(title: FBText.send, target: nil, action: nil)

    // State
    private var diagnostics: DiagnosticsReport?      // the instance shown is the instance sent
    private var collectingDiagnostics = false
    private var diagnosticsToken = 0
    private var diagTouched = false
    private var diagExpanded = false
    private var snapshotJPEG: Data?
    private var snapshotInfo: FeedbackReport.Snapshot?
    private var capturingSnapshot = false
    private var snapshotToken = 0
    private var consentAt: Date?
    private var marketingAt: Date?
    private var isSending = false
    private var finished = false
    private var positioned = false

    init(config: FeedbackConfig) {
        self.config = config
        let message = FeedbackWindowController.makeTextScroll(height: 140)
        messageScroll = message.scroll
        messageView = message.text
        let diag = FeedbackWindowController.makeTextScroll(height: 160)
        diagScroll = diag.scroll
        diagText = diag.text
        let win = FeedbackPanelWindow(contentRect: NSRect(x: 0, y: 0, width: 480, height: 620),
                                      styleMask: [.titled, .closable, .miniaturizable, .resizable],
                                      backing: .buffered, defer: false)
        super.init(window: win)
        win.delegate = self
        buildUI(in: win)
        restoreDraft()
        collectDiagnostics()
        validate()
    }

    required init?(coder: NSCoder) { return nil }

    // MARK: - Present / close
    func present() {
        guard let win = window else { return }
        if !positioned {
            positioned = true
            if !win.setFrameUsingName(FeedbackWindowController.autosaveName) { win.center() }
            _ = win.setFrameAutosaveName(FeedbackWindowController.autosaveName)
        }
        relayout()
        // Accessory (menu-bar) app: activate explicitly, otherwise the window opens behind others.
        if #available(macOS 14.0, *) { NSApp.activate() } else { NSApp.activate(ignoringOtherApps: true) }
        win.makeKeyAndOrderFront(nil)
        relayout()
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool { !isSending }

    func windowWillClose(_ notification: Notification) {
        NSObject.cancelPreviousPerformRequests(withTarget: self)
        snapshotToken += 1
        diagnosticsToken += 1
        if !finished { saveDraft() }                  // «Отмена» / close keeps the draft
        onClose?()
    }

    func windowDidResize(_ notification: Notification) { relayout() }

    // MARK: - UI
    private static func makeTextScroll(height: CGFloat) -> (scroll: NSScrollView, text: NSTextView) {
        let scroll = NSScrollView(frame: NSRect(x: 0, y: 0, width: rowWidth, height: height))
        scroll.hasVerticalScroller = true
        scroll.hasHorizontalScroller = false
        scroll.autohidesScrollers = true
        scroll.borderType = .bezelBorder
        let size = scroll.contentSize
        let text = NSTextView(frame: NSRect(x: 0, y: 0, width: size.width, height: size.height))
        text.minSize = NSSize(width: 0, height: size.height)
        text.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        text.isVerticallyResizable = true
        text.isHorizontallyResizable = false
        text.autoresizingMask = [.width]
        text.textContainer?.size = NSSize(width: size.width, height: CGFloat.greatestFiniteMagnitude)
        text.textContainer?.widthTracksTextView = true
        scroll.documentView = text
        scroll.translatesAutoresizingMaskIntoConstraints = false
        scroll.widthAnchor.constraint(equalToConstant: rowWidth).isActive = true
        scroll.heightAnchor.constraint(equalToConstant: height).isActive = true
        return (scroll, text)
    }

    private func buildUI(in win: NSWindow) {
        let appName = Bundle.main.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String ?? FBText.fallbackAppName
        win.title = FBText.windowTitlePrefix + appName
        win.isReleasedWhenClosed = false
        win.level = .normal
        win.contentMinSize = NSSize(width: 480, height: 460)
        win.contentMaxSize = NSSize(width: 480, height: 1600)
        win.autorecalculatesKeyViewLoop = true
        guard let content = win.contentView else { return }
        let w = FeedbackWindowController.rowWidth

        // 1. Intro
        let intro = NSTextField(wrappingLabelWithString: FBText.intro)
        styleText(intro, size: 12, color: .secondaryLabelColor, width: w)

        // 2. Topic (nothing selected at start; nothing selected at send → "other")
        categoryControl.selectedSegment = -1
        categoryControl.target = self
        categoryControl.action = #selector(categoryChanged)
        categoryControl.setAccessibilityLabel(FBText.topic)
        let topicGroup = column([heading(FBText.topic), categoryControl])

        // 3. Fish name, only for «Хочу рыбку»
        fishField.placeholderString = FBText.fishPlaceholder
        fishField.delegate = self
        fishField.setAccessibilityLabel(FBText.fishLabel)
        pinWidth(fishField, w)
        configureColumn(fishGroup, [heading(FBText.fishLabel), fishField])
        fishGroup.isHidden = true

        // 4. Message + placeholder overlay + counter
        messageView.isRichText = false
        messageView.importsGraphics = false
        messageView.allowsUndo = true
        messageView.font = .systemFont(ofSize: 13)
        messageView.textColor = .textColor
        messageView.textContainerInset = NSSize(width: 3, height: 5)
        messageView.isAutomaticQuoteSubstitutionEnabled = false
        messageView.isAutomaticDashSubstitutionEnabled = false
        messageView.isAutomaticTextReplacementEnabled = false
        messageView.isContinuousSpellCheckingEnabled = true
        messageView.delegate = self
        messageView.setAccessibilityLabel(FBText.messageLabel)
        messagePlaceholder.font = .systemFont(ofSize: 13)
        messagePlaceholder.textColor = .placeholderTextColor
        messagePlaceholder.translatesAutoresizingMaskIntoConstraints = false
        let messageBox = NSView()
        messageBox.translatesAutoresizingMaskIntoConstraints = false
        messageBox.addSubview(messageScroll)
        messageBox.addSubview(messagePlaceholder)
        NSLayoutConstraint.activate([
            messageScroll.leadingAnchor.constraint(equalTo: messageBox.leadingAnchor),
            messageScroll.trailingAnchor.constraint(equalTo: messageBox.trailingAnchor),
            messageScroll.topAnchor.constraint(equalTo: messageBox.topAnchor),
            messageScroll.bottomAnchor.constraint(equalTo: messageBox.bottomAnchor),
            messagePlaceholder.leadingAnchor.constraint(equalTo: messageBox.leadingAnchor, constant: 7),
            messagePlaceholder.topAnchor.constraint(equalTo: messageBox.topAnchor, constant: 6),
        ])
        counterLabel.font = .systemFont(ofSize: 11)
        counterLabel.textColor = .secondaryLabelColor
        counterLabel.alignment = .right
        pinWidth(counterLabel, w)
        let messageGroup = column([heading(FBText.messageLabel), messageBox, counterLabel])

        // 5. E-mail (optional) + inline error + note
        emailField.placeholderString = FBText.emailPlaceholder
        emailField.delegate = self
        emailField.setAccessibilityLabel(FBText.emailLabel)
        pinWidth(emailField, w)
        emailError.font = .systemFont(ofSize: 11)
        emailError.textColor = .systemRed
        emailError.isHidden = true
        let emailNote = NSTextField(wrappingLabelWithString: FBText.emailNote)
        styleText(emailNote, size: 11, color: .secondaryLabelColor, width: w)
        let emailGroup = column([heading(FBText.emailLabel), emailField, emailError, emailNote])

        // 5b. Early-users group: separate opt-in, unchecked, enabled only with a valid e-mail
        let marketingRow = checkRow(marketingBox, label: marketingLabel, size: 12,
                                    action: #selector(marketingChanged), labelClick: #selector(marketingLabelClicked))
        marketingBox.state = .off

        // 6. Snapshot (default OFF)
        snapshotBox.target = self
        snapshotBox.action = #selector(snapshotToggled)
        snapshotBox.state = .off
        snapshotThumb.imageScaling = .scaleProportionallyUpOrDown
        snapshotThumb.wantsLayer = true
        snapshotThumb.layer?.cornerRadius = 6
        snapshotThumb.layer?.masksToBounds = true
        snapshotThumb.translatesAutoresizingMaskIntoConstraints = false
        snapshotThumb.widthAnchor.constraint(equalToConstant: 192).isActive = true
        snapshotThumb.heightAnchor.constraint(equalToConstant: 108).isActive = true
        snapshotThumb.setAccessibilityLabel(FBText.snapshotToggle)
        snapshotThumb.isHidden = true
        styleText(snapshotCaption, size: 11, color: .secondaryLabelColor, width: w)
        snapshotCaption.isHidden = true
        let snapshotGroup = column([snapshotBox, snapshotThumb, snapshotCaption], spacing: 6)

        // 7. Diagnostics (default OFF; auto-ON for «Ошибка») + "what will be sent" disclosure
        diagBox.target = self
        diagBox.action = #selector(diagToggled)
        diagBox.state = .off
        styleLink(diagDisclosure, FBText.diagShow)
        diagDisclosure.target = self
        diagDisclosure.action = #selector(diagDisclosureClicked)
        diagText.isEditable = false
        diagText.isSelectable = true
        diagText.isRichText = false
        diagText.font = .monospacedSystemFont(ofSize: 11, weight: .regular)
        diagText.textColor = .textColor
        diagText.delegate = self
        diagText.setAccessibilityLabel(FBText.diagToggle)
        diagScroll.isHidden = true
        let diagGroup = column([diagBox, diagDisclosure, diagScroll], spacing: 6)

        configureColumn(form, [intro, topicGroup, fishGroup, messageGroup, emailGroup, marketingRow,
                               snapshotGroup, diagGroup], spacing: 12)
        form.translatesAutoresizingMaskIntoConstraints = false
        formDoc.addSubview(form)
        NSLayoutConstraint.activate([
            form.leadingAnchor.constraint(equalTo: formDoc.leadingAnchor, constant: 20),
            form.topAnchor.constraint(equalTo: formDoc.topAnchor, constant: 20),
        ])
        formScroll.documentView = formDoc
        formScroll.hasVerticalScroller = true
        formScroll.hasHorizontalScroller = false
        formScroll.autohidesScrollers = true
        formScroll.drawsBackground = false
        formScroll.borderType = .noBorder
        formScroll.translatesAutoresizingMaskIntoConstraints = false

        // 8–11. Footer: separator, consent (unchecked), privacy link, route line, status, buttons
        let separator = NSBox()
        separator.boxType = .separator
        pinWidth(separator, w)
        let consentRow = checkRow(consentBox, label: consentLabel, size: 12,
                                  action: #selector(consentChanged), labelClick: #selector(consentLabelClicked))
        consentBox.state = .off
        styleLink(privacyButton, FBText.privacy)
        privacyButton.target = self
        privacyButton.action = #selector(openPrivacy)
        privacyButton.isHidden = config.privacyPolicy == nil
        routeLabel.stringValue = config.routeText
        styleText(routeLabel, size: 11, color: .secondaryLabelColor, width: w)
        styleText(statusLabel, size: 11, color: .systemRed, width: w)
        statusLabel.isHidden = true

        progress.style = .spinning
        progress.controlSize = .small
        progress.isDisplayedWhenStopped = false
        progressLabel.font = .systemFont(ofSize: 11)
        progressLabel.textColor = .secondaryLabelColor
        progressLabel.isHidden = true
        cancelButton.target = self
        cancelButton.action = #selector(cancelClicked)
        cancelButton.keyEquivalent = "\u{1b}"
        sendButton.target = self
        sendButton.action = #selector(sendClicked)
        sendButton.keyEquivalent = "\r"                    // ⌘↩ sends; a plain Return types a newline
        sendButton.keyEquivalentModifierMask = [.command]
        sendButton.toolTip = "⌘↩"
        let buttons = NSStackView()
        buttons.orientation = .horizontal
        buttons.distribution = .gravityAreas
        buttons.spacing = 8
        buttons.addView(progress, in: .leading)
        buttons.addView(progressLabel, in: .leading)
        buttons.addView(cancelButton, in: .trailing)
        buttons.addView(sendButton, in: .trailing)
        pinWidth(buttons, w)

        let footer = NSStackView()
        configureColumn(footer, [separator, consentRow, privacyButton, routeLabel, statusLabel, buttons], spacing: 10)
        footer.translatesAutoresizingMaskIntoConstraints = false

        content.addSubview(formScroll)
        content.addSubview(footer)
        NSLayoutConstraint.activate([
            formScroll.topAnchor.constraint(equalTo: content.topAnchor),
            formScroll.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            formScroll.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            formScroll.bottomAnchor.constraint(equalTo: footer.topAnchor, constant: -10),
            footer.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 20),
            footer.bottomAnchor.constraint(equalTo: content.bottomAnchor, constant: -16),
        ])
        win.initialFirstResponder = messageView
    }

    /// The form scrolls inside a fixed-height window; the document view is sized by hand
    /// (frame-based) to the stack's fitting height, so no constraints touch the clip view.
    private func relayout() {
        guard let content = window?.contentView else { return }
        content.layoutSubtreeIfNeeded()
        let fit = form.fittingSize
        let clip = formScroll.contentView.bounds.size
        formDoc.frame = NSRect(x: 0, y: 0, width: clip.width, height: max(clip.height, ceil(fit.height) + 32))
    }

    private func configureColumn(_ stack: NSStackView, _ views: [NSView], spacing: CGFloat = 4) {
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = spacing
        stack.detachesHiddenViews = true
        stack.setHuggingPriority(.defaultHigh, for: .vertical)
        for v in views { stack.addArrangedSubview(v) }
    }

    private func column(_ views: [NSView], spacing: CGFloat = 4) -> NSStackView {
        let stack = NSStackView()
        configureColumn(stack, views, spacing: spacing)
        return stack
    }

    private func heading(_ text: String) -> NSTextField {
        let label = NSTextField(labelWithString: text)
        label.font = .systemFont(ofSize: 13, weight: .semibold)
        return label
    }

    private func styleText(_ label: NSTextField, size: CGFloat, color: NSColor, width: CGFloat) {
        label.font = .systemFont(ofSize: size)
        label.textColor = color
        label.isSelectable = false
        label.preferredMaxLayoutWidth = width
        pinWidth(label, width)
    }

    private func styleLink(_ button: NSButton, _ title: String) {
        button.isBordered = false
        button.attributedTitle = NSAttributedString(string: title, attributes: [
            .foregroundColor: NSColor.linkColor,
            .font: NSFont.systemFont(ofSize: 12),
        ])
        button.setAccessibilityLabel(title)
    }

    /// Checkbox with an empty title + a wrapping label that also toggles it on click.
    private func checkRow(_ box: NSButton, label: NSTextField, size: CGFloat,
                          action: Selector, labelClick: Selector) -> NSStackView {
        box.title = ""
        box.target = self
        box.action = action
        box.setAccessibilityLabel(label.stringValue)
        label.font = .systemFont(ofSize: size)
        label.textColor = .labelColor
        label.isSelectable = false
        label.preferredMaxLayoutWidth = 410
        pinWidth(label, 410)
        label.addGestureRecognizer(NSClickGestureRecognizer(target: self, action: labelClick))
        let row = NSStackView(views: [box, label])
        row.orientation = .horizontal
        row.alignment = .top
        row.spacing = 6
        return row
    }

    private func pinWidth(_ view: NSView, _ width: CGFloat) {
        view.translatesAutoresizingMaskIntoConstraints = false
        let c = view.widthAnchor.constraint(equalToConstant: width)
        c.priority = NSLayoutConstraint.Priority(999)
        c.isActive = true
    }

    // MARK: - Inputs
    private var trimmedEmail: String { emailField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines) }
    private var emailOK: Bool { trimmedEmail.isEmpty || FBValidate.isEmail(trimmedEmail) }
    private var trimmedFish: String { fishField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines) }
    private var selectedCategory: FBCategory? { FBCategory.from(segment: categoryControl.selectedSegment) }

    @objc private func categoryChanged() {
        fishGroup.isHidden = selectedCategory != .fishRequest
        if selectedCategory == .bug && !diagTouched && diagBox.state == .off {
            diagBox.state = .on
            collectDiagnostics()
        }
        contentChanged()
        relayout()
    }

    @objc private func consentChanged() {
        consentAt = consentBox.state == .on ? Date() : nil
        validate()
    }

    @objc private func consentLabelClicked() {
        guard consentBox.isEnabled else { return }
        consentBox.state = consentBox.state == .on ? .off : .on
        consentChanged()
    }

    @objc private func marketingChanged() {
        marketingAt = marketingBox.state == .on ? Date() : nil
    }

    @objc private func marketingLabelClicked() {
        guard marketingBox.isEnabled else { return }
        marketingBox.state = marketingBox.state == .on ? .off : .on
        marketingChanged()
    }

    @objc private func openPrivacy() {
        if let url = config.privacyPolicy { _ = NSWorkspace.shared.open(url) }
    }

    @objc private func cancelClicked() { window?.close() }

    // NSTextView (message): hard cap 2000 while typing, pastes truncated, control characters stripped.
    func textView(_ textView: NSTextView, shouldChangeTextIn affectedCharRange: NSRange,
                  replacementString: String?) -> Bool {
        guard textView === messageView, let replacement = replacementString, !replacement.isEmpty,
              !textView.hasMarkedText() else { return true }
        let remaining = (textView.string as NSString).replacingCharacters(in: affectedCharRange, with: "")
        let room = FBLimit.messageMax - remaining.count
        let cleaned = FBValidate.stripControls(replacement)
        if cleaned == replacement && cleaned.count <= room { return true }
        let fitted = String(cleaned.prefix(max(0, room)))
        if fitted.isEmpty { NSSound.beep(); return false }
        if textView.shouldChangeText(in: affectedCharRange, replacementString: fitted) {
            textView.replaceCharacters(in: affectedCharRange, with: fitted)
            textView.didChangeText()
        }
        return false
    }

    // Tab moves focus instead of typing a tab (Option-Tab still inserts one).
    func textView(_ textView: NSTextView, doCommandBy commandSelector: Selector) -> Bool {
        if commandSelector == #selector(NSResponder.insertTab(_:)) {
            textView.window?.selectNextKeyView(nil)
            return true
        }
        if commandSelector == #selector(NSResponder.insertBacktab(_:)) {
            textView.window?.selectPreviousKeyView(nil)
            return true
        }
        return false
    }

    func textDidChange(_ notification: Notification) {
        guard let tv = notification.object as? NSTextView, tv === messageView else { return }
        contentChanged()
    }

    func controlTextDidChange(_ obj: Notification) {
        guard let field = obj.object as? NSTextField else { return }
        if field === fishField && fishField.stringValue.count > FBLimit.fishMax {
            fishField.stringValue = String(fishField.stringValue.prefix(FBLimit.fishMax))
        }
        if field === emailField { scheduleEmailCheck() }
        contentChanged()
    }

    func controlTextDidEndEditing(_ obj: Notification) {
        guard let field = obj.object as? NSTextField, field === emailField else { return }
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(updateEmailError), object: nil)
        updateEmailError()
    }

    /// Hide the e-mail error at once when the address becomes valid; show it after a pause while typing.
    private func scheduleEmailCheck() {
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(updateEmailError), object: nil)
        if emailOK {
            updateEmailError()
        } else {
            perform(#selector(updateEmailError), with: nil, afterDelay: 0.8)
        }
    }

    @objc private func updateEmailError() {
        let show = !emailOK
        if emailError.isHidden == show {
            emailError.isHidden = !show
            relayout()
        }
    }

    /// Any edit: draft saved 0.5 s after the last change, Send state refreshed.
    private func contentChanged() {
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(saveDraft), object: nil)
        perform(#selector(saveDraft), with: nil, afterDelay: 0.5)
        validate()
    }

    @objc private func revalidate() { validate() }

    private func validate() {
        let count = FBValidate.cleanMessage(messageView.string).count
        messagePlaceholder.isHidden = !messageView.string.isEmpty
        let short = count > 0 && count < FBLimit.messageMin
        counterLabel.stringValue = short ? "\(FBText.minLengthHint) · \(count) / \(FBLimit.messageMax)"
                                         : "\(count) / \(FBLimit.messageMax)"
        counterLabel.textColor = short ? .systemRed : .secondaryLabelColor

        let canOptIn = !trimmedEmail.isEmpty && emailOK
        if !canOptIn && marketingBox.state == .on {
            marketingBox.state = .off
            marketingAt = nil
        }
        marketingBox.isEnabled = canOptIn && !isSending
        marketingLabel.textColor = canOptIn ? .labelColor : .tertiaryLabelColor

        let limited = FeedbackRateLimit.isLimited
        setStatus(limited ? FBText.rateLimited : nil)
        if limited {   // the limit expires by itself: look again in 30 s
            NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(revalidate), object: nil)
            perform(#selector(revalidate), with: nil, afterDelay: 30)
        }

        let diagnosticsBusy = diagBox.state == .on && (collectingDiagnostics || diagnostics == nil)
        sendButton.isEnabled = count >= FBLimit.messageMin && count <= FBLimit.messageMax
            && emailOK && trimmedFish.count <= FBLimit.fishMax
            && consentBox.state == .on && !limited && !isSending
            && !capturingSnapshot && !diagnosticsBusy
        cancelButton.isEnabled = !isSending
    }

    private func setStatus(_ text: String?) {
        statusLabel.stringValue = text ?? ""
        let hidden = text == nil
        if statusLabel.isHidden != hidden {
            statusLabel.isHidden = hidden
            relayout()
        }
    }

    // MARK: - Draft
    @objc private func saveDraft() {
        FeedbackDraft.save(.init(category: selectedCategory?.rawValue ?? "", message: messageView.string,
                                 email: emailField.stringValue, fish: fishField.stringValue))
    }

    private func restoreDraft() {
        if let d = FeedbackDraft.load() {
            if let c = FBCategory(rawValue: d.category) { categoryControl.selectedSegment = c.segment }
            messageView.string = String(d.message.prefix(FBLimit.messageMax))
            emailField.stringValue = d.email
            fishField.stringValue = String(d.fish.prefix(FBLimit.fishMax))
        }
        if trimmedEmail.isEmpty, let last = FeedbackDraft.lastEmail { emailField.stringValue = last }
        fishGroup.isHidden = selectedCategory != .fishRequest
        if selectedCategory == .bug { diagBox.state = .on }      // same auto-ON rule as a fresh choice
        emailError.isHidden = emailOK
    }

    // MARK: - Diagnostics
    @objc private func diagToggled() {
        diagTouched = true
        if diagBox.state == .on { collectDiagnostics() }      // re-collect when switched ON
        validate()
    }

    @objc private func diagDisclosureClicked() {
        diagExpanded.toggle()
        styleLink(diagDisclosure, diagExpanded ? FBText.diagHide : FBText.diagShow)
        diagScroll.isHidden = !diagExpanded
        renderDiagnostics()
        relayout()
        if diagExpanded { _ = diagScroll.scrollToVisible(diagScroll.bounds) }
    }

    private func collectDiagnostics() {
        diagnosticsToken += 1
        let token = diagnosticsToken
        collectingDiagnostics = true
        renderDiagnostics()
        validate()
        Diagnostics.collect { [weak self] report in
            guard let self = self, token == self.diagnosticsToken else { return }
            self.diagnostics = report
            self.collectingDiagnostics = false
            self.renderDiagnostics()
            self.validate()
        }
    }

    /// Shows exactly the instance that will be sent (pretty-printed, sorted keys).
    private func renderDiagnostics() {
        if let d = diagnostics {
            diagText.string = Diagnostics.json(d, pretty: true)
        } else {
            diagText.string = collectingDiagnostics ? FBText.diagCollecting : ""
        }
    }

    // MARK: - Snapshot (main-screen aquarium only, via WKWebView.takeSnapshot)
    @objc private func snapshotToggled() {
        snapshotToken += 1
        snapshotJPEG = nil
        snapshotInfo = nil
        snapshotThumb.image = nil
        snapshotThumb.isHidden = true
        guard snapshotBox.state == .on else {
            capturingSnapshot = false
            snapshotCaption.isHidden = true
            relayout()
            validate()
            return
        }
        let token = snapshotToken
        capturingSnapshot = true
        snapshotCaption.stringValue = FBText.snapshotTaking
        snapshotCaption.textColor = .secondaryLabelColor
        snapshotCaption.isHidden = false
        relayout()
        validate()
        guard let webView = WallpaperProbe.mainWebView() else { snapshotFailed(); return }
        WallpaperProbe.snapshot(webView) { [weak self] image in
            guard let self = self, token == self.snapshotToken else { return }
            guard let cg = image?.cgImage(forProposedRect: nil, context: nil, hints: nil),
                  let jpeg = SnapshotEncoder.jpeg(from: cg) else { self.snapshotFailed(); return }
            self.capturingSnapshot = false
            self.snapshotJPEG = jpeg.data
            self.snapshotInfo = FeedbackReport.Snapshot(width: jpeg.width, height: jpeg.height, bytes: jpeg.data.count)
            self.snapshotThumb.image = NSImage(data: jpeg.data)
            self.snapshotThumb.isHidden = false
            self.snapshotCaption.stringValue = FBText.snapshotCaption
            self.relayout()
            self.validate()
        }
    }

    private func snapshotFailed() {
        capturingSnapshot = false
        snapshotJPEG = nil
        snapshotInfo = nil
        snapshotBox.state = .off
        snapshotThumb.isHidden = true
        snapshotCaption.stringValue = FBText.snapshotFailed
        snapshotCaption.textColor = .systemRed
        snapshotCaption.isHidden = false
        relayout()
        validate()
    }

    // MARK: - Send
    private func makeReport() -> FeedbackReport {
        let now = Date()
        let id = UUID().uuidString.lowercased()
        let category = selectedCategory ?? .other
        let email = trimmedEmail
        let fish = trimmedFish
        var snapshot: FeedbackReport.Snapshot? = nil
        if snapshotBox.state == .on, snapshotJPEG != nil, var s = snapshotInfo {
            s.file = "\(id).jpg"
            snapshot = s
        }
        var marketing: FeedbackReport.Marketing? = nil
        if marketingBox.state == .on && !email.isEmpty {
            marketing = FeedbackReport.Marketing(optIn: true, version: FBText.marketingVersion,
                                                 at: FBDate.string(marketingAt ?? now))
        }
        return FeedbackReport(
            id: id,
            createdAt: FBDate.string(now),
            category: category.rawValue,
            message: FBValidate.cleanMessage(messageView.string),
            fishRequest: category == .fishRequest && !fish.isEmpty ? String(fish.prefix(FBLimit.fishMax)) : nil,
            email: email.isEmpty ? nil : email,
            consent: FeedbackReport.Consent(given: true, version: FBText.consentVersion,
                                            at: FBDate.string(consentAt ?? now)),
            marketing: marketing,
            app: FeedbackReport.AppInfo.current,
            diagnostics: diagBox.state == .on ? diagnostics : nil,
            snapshot: snapshot,
            delivery: nil)
    }

    @objc private func sendClicked() {
        validate()
        guard sendButton.isEnabled, !isSending else { NSSound.beep(); return }
        var report = makeReport()
        let jpeg = report.snapshot != nil ? snapshotJPEG : nil
        report.delivery = FeedbackReport.Delivery(route: config.route.rawValue, status: "pending", attempts: 0)
        // 1. Always save locally first; delivery continues even if that fails.
        var saveError: String? = nil
        do { try FeedbackStore.save(report, jpeg: jpeg) } catch { saveError = error.localizedDescription }
        if let email = report.email { FeedbackDraft.lastEmail = email }
        // 2. Route: endpoint → mailto → clipboard.
        if let endpoint = config.endpoint {
            postRoute(report, jpeg: jpeg, endpoint: endpoint, saveError: saveError)
        } else if let address = config.email {
            mailRoute(report, address: address, saveError: saveError)
        } else {
            clipboardRoute(report, saveError: saveError)
        }
    }

    private func postRoute(_ report: FeedbackReport, jpeg: Data?, endpoint: URL, saveError: String?) {
        setSending(true)
        FeedbackDelivery.post(report, jpeg: jpeg, to: endpoint) { [weak self] outcome in
            guard let self = self else { return }
            self.setSending(false)
            var r = report
            var d = r.delivery ?? FeedbackReport.Delivery(route: FeedbackConfig.Route.endpoint.rawValue,
                                                          status: "pending", attempts: 0)
            d.attempts += 1
            d.lastAttemptAt = FBDate.string(Date())
            switch outcome {
            case .sent(let ticket):
                d.status = "sent"
                d.ticket = ticket
                d.lastError = nil
                r.delivery = d
                FeedbackStore.update(r)
                let info = r.email.map { FBText.sentReply($0) } ?? ""
                self.showAlert(FBText.sentTitle, info: info, saveError: saveError, buttons: [FBText.done]) { _ in
                    self.finish()
                }
            case .retryLater(let reason):
                d.status = "pending"                  // the retry queue sends it later
                d.lastError = String(reason.prefix(200))
                r.delivery = d
                FeedbackStore.update(r)
                let address = self.config.email
                let buttons = address == nil ? [FBText.done] : [FBText.done, FBText.sendByMail]
                self.showAlert(FBText.pendingTitle, info: "", saveError: saveError, buttons: buttons) { index in
                    if index == 1, let address = address {
                        self.mailRoute(r, address: address, saveError: nil)
                    } else {
                        self.finish()
                    }
                }
            case .rejected(let code):
                d.status = "failed"                   // window stays open, text intact
                d.lastError = "HTTP \(code)"
                r.delivery = d
                FeedbackStore.update(r)
                let address = self.config.email
                let alternative = address == nil ? FBText.copy : FBText.sendByMail
                self.showAlert(FBText.rejectedTitle(code), info: "", saveError: saveError,
                               buttons: [alternative, FBText.close], style: .warning) { index in
                    guard index == 0 else { return }
                    if let address = address {
                        self.mailRoute(r, address: address, saveError: nil)
                    } else {
                        self.clipboardRoute(r, saveError: nil)
                    }
                }
            }
        }
    }

    private func mailRoute(_ report: FeedbackReport, address: String, saveError: String?) {
        guard let url = FeedbackDelivery.mailtoURL(for: report, to: address), NSWorkspace.shared.open(url) else {
            clipboardRoute(report, saveError: saveError)      // no mail client → clipboard
            return
        }
        var r = report
        r.delivery = FeedbackReport.Delivery(route: FeedbackConfig.Route.mailto.rawValue, status: "handed_off",
                                             attempts: (report.delivery?.attempts ?? 0) + 1,
                                             lastAttemptAt: FBDate.string(Date()))
        FeedbackStore.update(r)
        var info = ""
        if r.snapshot != nil, let jpg = FeedbackStore.fileURL(id: r.id, ext: "jpg"),
           FileManager.default.fileExists(atPath: jpg.path) {
            NSWorkspace.shared.activateFileViewerSelecting([jpg])
            info = FBText.dragSnapshot(r.id)
        }
        showAlert(FBText.mailOpened, info: info, saveError: saveError, buttons: [FBText.done]) { [weak self] _ in
            self?.finish()
        }
    }

    private func clipboardRoute(_ report: FeedbackReport, saveError: String?) {
        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()
        pasteboard.setString(FeedbackDelivery.clipboardText(for: report), forType: .string)
        var r = report
        r.delivery = FeedbackReport.Delivery(route: FeedbackConfig.Route.clipboard.rawValue, status: "handed_off",
                                             attempts: (report.delivery?.attempts ?? 0) + 1,
                                             lastAttemptAt: FBDate.string(Date()))
        FeedbackStore.update(r)
        let json = saveError == nil ? FeedbackStore.fileURL(id: r.id, ext: "json") : nil
        var lines: [String] = []
        if let json = json { lines.append(FBText.copiedSaved((json.path as NSString).abbreviatingWithTildeInPath)) }
        if let address = config.email { lines.append(FBText.developerAddress(address)) }
        let buttons = json == nil ? [FBText.done] : [FBText.showInFinder, FBText.done]
        showAlert(FBText.copiedTitle, info: lines.joined(separator: "\n"), saveError: saveError,
                  buttons: buttons) { [weak self] index in
            if index == 0, let json = json { NSWorkspace.shared.activateFileViewerSelecting([json]) }
            self?.finish()
        }
    }

    private func setSending(_ on: Bool) {
        isSending = on
        if on { progress.startAnimation(nil) } else { progress.stopAnimation(nil) }
        progressLabel.isHidden = !on
        let controls: [NSControl] = [categoryControl, fishField, emailField, snapshotBox, diagBox, consentBox]
        for c in controls { c.isEnabled = !on }
        messageView.isEditable = !on
        validate()
    }

    /// Sent, handed off or pending: clear the draft, count the send, close.
    private func finish() {
        finished = true
        FeedbackDraft.clear()
        FeedbackRateLimit.record()
        window?.close()
    }

    private func showAlert(_ title: String, info: String, saveError: String?, buttons: [String],
                           style: NSAlert.Style = .informational, then: @escaping (Int) -> Void) {
        let alert = NSAlert()
        alert.messageText = title
        var parts: [String] = []
        if !info.isEmpty { parts.append(info) }
        if let e = saveError { parts.append(FBText.saveFailed(e)) }
        alert.informativeText = parts.joined(separator: "\n\n")
        alert.alertStyle = style
        for b in buttons { alert.addButton(withTitle: b) }
        guard let win = window else { then(0); return }
        alert.beginSheetModal(for: win) { response in
            let index = response.rawValue - NSApplication.ModalResponse.alertFirstButtonReturn.rawValue
            DispatchQueue.main.async { then(index) }      // let the sheet finish closing first
        }
    }
}

// MARK: - Small helpers

/// Top-left origin, so the scrolling form starts at its top.
final class FlippedView: NSView {
    override var isFlipped: Bool { true }
}

/// Placeholder text over the message view; clicks go through to the text view.
final class PassthroughLabel: NSTextField {
    override func hitTest(_ point: NSPoint) -> NSView? { nil }
}

/// A menu-bar (LSUIElement) app has no Edit menu, so ⌘X/⌘C/⌘V/⌘A/⌘Z/⌘W would do nothing in the
/// form. Route them to the responder chain here (works with Cyrillic layouts via the key code).
final class FeedbackPanelWindow: NSWindow {
    private static let keys: [UInt16: String] = [7: "x", 8: "c", 9: "v", 0: "a", 6: "z", 13: "w"]

    override func performKeyEquivalent(with event: NSEvent) -> Bool {
        let flags = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
        guard event.type == .keyDown, flags == .command || flags == [.command, .shift] else {
            return super.performKeyEquivalent(with: event)
        }
        let typed = [event.characters, event.charactersIgnoringModifiers].compactMap { $0?.lowercased() }
        var key = typed.first { FeedbackPanelWindow.keys.values.contains($0) }
        if key == nil, let raw = event.charactersIgnoringModifiers, !raw.unicodeScalars.allSatisfy({ $0.isASCII }) {
            key = FeedbackPanelWindow.keys[event.keyCode]     // non-Latin layout: physical QWERTY key
        }
        var action: Selector?
        switch key {
        case "x"?: action = #selector(NSText.cut(_:))
        case "c"?: action = #selector(NSText.copy(_:))
        case "v"?: action = #selector(NSText.paste(_:))
        case "a"?: action = #selector(NSText.selectAll(_:))
        case "z"?: action = flags.contains(.shift) ? Selector(("redo:")) : Selector(("undo:"))
        case "w"?:
            performClose(nil)
            return true
        default: action = nil
        }
        if let action = action, NSApp.sendAction(action, to: nil, from: self) { return true }
        return super.performKeyEquivalent(with: event)
    }
}
