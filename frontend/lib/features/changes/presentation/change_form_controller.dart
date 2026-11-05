import 'dart:async';

import 'package:flutter/widgets.dart';

import '../../../core/api_error.dart';
import '../../../core/time.dart';
import '../data/changes_api.dart';
import '../data/models.dart';

/// Minimal CI reference kept by the form (chips).
@immutable
class CiRef {
  const CiRef({required this.id, required this.identifier, required this.name});

  final String id;
  final String identifier;
  final String name;
}

/// State of the change form (§10.3).
///
/// - Holds the last server version ([base]) and the local edits; [pendingFields]
///   is exactly what a PATCH would send (only fields the API lists in
///   `editable_fields` and that differ from [base]).
/// - Every PATCH carries [Change.version]; a 409 `change.version_conflict`
///   stops autosave and is shown until the user reloads ([reload]).
/// - Autosave every [autosaveInterval] while there are unsaved edits.
/// - [inlineErrors] only mirror backend rules for UX; the authority is
///   `GET /readiness` ([readiness]).
class ChangeFormController extends ChangeNotifier {
  ChangeFormController({
    required this.api,
    required this.companyId,
    required Change initial,
    this.autosaveInterval = const Duration(seconds: 30),
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now,
       base = initial {
    for (final controller in _texts.values) {
      controller.addListener(notifyListeners);
    }
    _load(initial);
  }

  final ChangesApi api;
  final String companyId;
  final Duration autosaveInterval;
  final DateTime Function() _clock;

  /// Last version known from the server.
  Change base;

  static const List<String> textFields = [
    'title',
    'description',
    'implementation_plan',
    'rollback_plan',
    'impact',
    'requirement_ref',
    'ticket_ref',
  ];

  late final Map<String, TextEditingController> _texts = {
    for (final field in textFields) field: TextEditingController(),
  };

  TextEditingController text(String field) => _texts[field]!;

  String? categoryId;
  String? subcategoryId;
  String? changeType;
  String? risk;
  String? assigneeId;
  String? approverId;
  String? verifierId;
  DateTime? windowStart;
  DateTime? windowEnd;
  List<CiRef> cis = const [];

  bool saving = false;
  DateTime? lastSavedAt;

  /// 409 conflict: autosave stops until [reload].
  ApiProblem? conflict;

  /// Last failed save (other than a conflict).
  ApiProblem? saveError;

  Readiness? readiness;
  Object? readinessError;

  Timer? _timer;
  bool _disposed = false;

  bool canEdit(String field) => base.editableFields.contains(field);

  void _load(Change change) {
    base = change;
    String? value(String field) => switch (field) {
      'title' => change.title,
      'description' => change.description,
      'implementation_plan' => change.implementationPlan,
      'rollback_plan' => change.rollbackPlan,
      'impact' => change.impact,
      'requirement_ref' => change.requirementRef,
      'ticket_ref' => change.ticketRef,
      _ => null,
    };
    for (final field in textFields) {
      _texts[field]!.value = TextEditingValue(text: value(field) ?? '');
    }
    categoryId = change.category?.id;
    subcategoryId = change.subcategory?.id;
    changeType = change.changeType;
    risk = change.risk;
    assigneeId = change.assignee?.id;
    approverId = change.approver?.id;
    verifierId = change.verifier?.id;
    windowStart = change.windowStart;
    windowEnd = change.windowEnd;
    cis = [
      for (final ci in change.ci)
        CiRef(id: ci.id, identifier: ci.identifier, name: ci.name),
    ];
  }

  /// Starts the autosave timer.
  void startAutosave() {
    _timer?.cancel();
    _timer = Timer.periodic(autosaveInterval, (_) {
      if (dirty && !saving && !paused) unawaited(save(auto: true));
    });
  }

  // ------------------------------------------------------------- edits

  void update(void Function() edit) {
    edit();
    notifyListeners();
  }

  void setCategory(String? id, {String? defaultRisk}) => update(() {
    if (id != categoryId) subcategoryId = null;
    categoryId = id;
    // Suggest the category's default risk, never overriding a choice.
    if (risk == null && defaultRisk != null && canEdit('risk')) {
      risk = defaultRisk;
    }
  });

  void addCi(CiRef ci) => update(() {
    if (!cis.any((c) => c.id == ci.id)) cis = [...cis, ci];
  });

  void removeCi(String id) => update(
    () => cis = [
      for (final c in cis)
        if (c.id != id) c,
    ],
  );

  // ------------------------------------------------------------- diff

  static const List<String> _fields = [
    ...textFields,
    'category_id',
    'subcategory_id',
    'change_type',
    'risk',
    'assignee_id',
    'approver_id',
    'verifier_id',
    'window_start',
    'window_end',
    'ci_ids',
  ];

  static String? _textOrNull(String? value) =>
      value == null || value.isEmpty ? null : value;

  /// Value of [field] in a server version of the change.
  static Object? serverValue(Change c, String field) => switch (field) {
    'title' => _textOrNull(c.title),
    'description' => _textOrNull(c.description),
    'implementation_plan' => _textOrNull(c.implementationPlan),
    'rollback_plan' => _textOrNull(c.rollbackPlan),
    'impact' => _textOrNull(c.impact),
    'requirement_ref' => _textOrNull(c.requirementRef),
    'ticket_ref' => _textOrNull(c.ticketRef),
    'category_id' => c.category?.id,
    'subcategory_id' => c.subcategory?.id,
    'change_type' => c.changeType,
    'risk' => c.risk,
    'assignee_id' => c.assignee?.id,
    'approver_id' => c.approver?.id,
    'verifier_id' => c.verifier?.id,
    'window_start' => c.windowStart,
    'window_end' => c.windowEnd,
    'ci_ids' => [for (final ci in c.ci) ci.id],
    _ => null,
  };

  /// Value of [field] in the form.
  Object? localValue(String field) => switch (field) {
    'category_id' => categoryId,
    'subcategory_id' => subcategoryId,
    'change_type' => changeType,
    'risk' => risk,
    'assignee_id' => assigneeId,
    'approver_id' => approverId,
    'verifier_id' => verifierId,
    'window_start' => windowStart,
    'window_end' => windowEnd,
    'ci_ids' => [for (final c in cis) c.id],
    _ => _textOrNull(_texts[field]?.text),
  };

  static bool _same(Object? a, Object? b) {
    if ((a == null || a is DateTime) && (b == null || b is DateTime)) {
      return WarsawTime.sameInstant(a as DateTime?, b as DateTime?);
    }
    if (a is List && b is List) {
      return a.length == b.length && a.toSet().containsAll(b);
    }
    return a == b;
  }

  static Object? _toApi(Object? value) =>
      value is DateTime ? value.toUtc().toIso8601String() : value;

  /// Edited fields as the PATCH body against [against] (default: [base]);
  /// only fields the API lists in `editable_fields`; `null` clears a field.
  Map<String, Object?> pendingFields([Change? against]) {
    final other = against ?? base;
    return {
      for (final field in _fields)
        if (other.editableFields.contains(field) &&
            !_same(localValue(field), serverValue(other, field)))
          field: _toApi(localValue(field)),
    };
  }

  bool get dirty => pendingFields().isNotEmpty;

  // ------------------------------------------------------------- inline UX

  /// Field → message. Mirrors backend rules (§4.3) only for immediate
  /// feedback; `GET /readiness` stays the source of truth.
  Map<String, String> get inlineErrors {
    final errors = <String, String>{};
    final high = risk == 'high';
    if (high && _texts['rollback_plan']!.text.trim().isEmpty) {
      errors['rollback_plan'] =
          'Plan wycofania jest wymagany przy wysokim ryzyku.';
    }
    if (high && (windowStart == null || windowEnd == null)) {
      errors['window_start'] =
          'Okno serwisowe (od i do) jest wymagane przy wysokim ryzyku.';
    } else if ((windowStart == null) != (windowEnd == null)) {
      errors['window_start'] =
          'Podaj początek i koniec okna albo pozostaw oba puste.';
    }
    if (windowStart != null &&
        windowEnd != null &&
        !windowStart!.isBefore(windowEnd!)) {
      errors['window_end'] =
          'Koniec okna musi być późniejszy niż jego początek.';
    }
    if (approverId != null &&
        (approverId == base.requestedBy.id || approverId == assigneeId)) {
      errors['approver_id'] =
          'Zasada czterech oczu: zatwierdzający nie może być zgłaszającym ani '
          'wykonawcą.';
    }
    if (_texts['title']!.text.length > 500) {
      errors['title'] = 'Tytuł może mieć najwyżej 500 znaków.';
    }
    return errors;
  }

  // ------------------------------------------------------------- server

  /// Autosave and saving are stopped (conflict or a blocking error).
  bool get paused => conflict != null || blocked != null;

  /// 409 other than a version conflict (`change.frozen`, `company.archived`,
  /// ...) or 422 `change.field_not_editable`: saving cannot succeed with the
  /// current state; autosave stops and the server state is reloaded.
  ApiProblem? blocked;

  /// Server version fetched after a conflict (for [conflictDiffs]).
  Change? serverVersion;

  Future<bool>? _inFlight;

  /// Waits for a save in progress.
  Future<void> idle() async {
    final pending = _inFlight;
    if (pending != null) await pending;
  }

  /// PATCH of the pending fields with the current version.
  /// Returns false on a conflict or error (see [conflict], [blocked],
  /// [saveError]).
  Future<bool> save({bool auto = false}) {
    if (saving) return _inFlight ?? Future.value(false);
    if (paused) return Future.value(false);
    final future = _save();
    _inFlight = future;
    return future.whenComplete(() => _inFlight = null);
  }

  Future<bool> _save() async {
    final fields = pendingFields();
    if (fields.isEmpty) return true;
    saving = true;
    saveError = null;
    notifyListeners();
    try {
      final updated = await api.update(
        companyId,
        base.id,
        version: base.version,
        fields: fields,
      );
      // Edits typed while the request was in flight stay pending: only the
      // base moves forward.
      base = updated;
      final known = {for (final c in updated.ci) c.id: c};
      cis = [
        for (final c in cis)
          known[c.id] == null
              ? c
              : CiRef(
                  id: c.id,
                  identifier: known[c.id]!.identifier,
                  name: known[c.id]!.name,
                ),
      ];
      lastSavedAt = _clock();
      if (!_disposed) unawaited(refreshReadiness());
      return true;
    } on Object catch (error) {
      final problem = ApiProblem.from(error);
      if (problem.isVersionConflict) {
        conflict = problem;
        unawaited(_fetchServerVersion());
      } else if (problem.status == 409 ||
          problem.code == 'change.field_not_editable') {
        blocked = problem;
        unawaited(_refreshBase());
      } else {
        saveError = problem;
      }
      return false;
    } finally {
      saving = false;
      if (!_disposed) notifyListeners();
    }
  }

  Future<void> refreshReadiness() async {
    try {
      readiness = await api.readiness(companyId, base.id);
      readinessError = null;
    } on Object catch (error) {
      readinessError = error;
    }
    if (!_disposed) notifyListeners();
  }

  Future<void> _fetchServerVersion() async {
    try {
      serverVersion = await api.getChange(companyId, base.id);
    } on Object {
      serverVersion = null;
    }
    if (!_disposed) notifyListeners();
  }

  /// After a blocking error: take the server's state (status,
  /// `editable_fields`) without touching the values typed in the form.
  Future<void> _refreshBase() async {
    try {
      base = await api.getChange(companyId, base.id);
    } on Object {
      return;
    }
    if (_disposed) return;
    notifyListeners();
    await refreshReadiness();
  }

  /// Fields that differ between the form and the newer server version:
  /// (field, local value, server value), API representation.
  List<(String, Object?, Object?)> get conflictDiffs {
    final server = serverVersion;
    if (server == null) return const [];
    return [
      for (final entry in pendingFields(server).entries)
        (entry.key, entry.value, _toApi(serverValue(server, entry.key))),
    ];
  }

  /// Conflict: keep my values and save them on top of the newer version.
  Future<bool> overwriteWithMine() async {
    final server = serverVersion ?? await api.getChange(companyId, base.id);
    base = server;
    conflict = null;
    serverVersion = null;
    notifyListeners();
    return save();
  }

  /// Conflict or blocking error: drop my values, load the server version.
  Future<void> discardMine() async {
    final fresh = await api.getChange(companyId, base.id);
    conflict = null;
    blocked = null;
    serverVersion = null;
    saveError = null;
    _load(fresh);
    notifyListeners();
    await refreshReadiness();
  }

  /// Before leaving the form: waits for a running save and saves the rest.
  /// True = nothing unsaved remains.
  Future<bool> saveBeforeLeaving() async {
    await idle();
    if (!dirty) return true;
    if (paused) return false;
    return save();
  }

  @override
  void dispose() {
    _disposed = true;
    _timer?.cancel();
    for (final controller in _texts.values) {
      controller.dispose();
    }
    super.dispose();
  }
}
