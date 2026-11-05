import '../../../core/change_status.dart';
import '../../../core/session.dart';
import '../../../core/time.dart';
import '../data/models.dart';

/// Polish labels of change fields (forms, diffs, readiness).
const Map<String, String> changeFieldLabels = {
  'title': 'Tytuł',
  'category_id': 'Kategoria',
  'subcategory_id': 'Podkategoria',
  'change_type': 'Typ zmiany',
  'risk': 'Ryzyko',
  'description': 'Opis i uzasadnienie',
  'implementation_plan': 'Plan wdrożenia',
  'rollback_plan': 'Plan wycofania',
  'impact': 'Wpływ',
  'requirement_ref': 'Podstawa / wymóg',
  'ticket_ref': 'Zgłoszenie',
  'assignee_id': 'Wykonawca',
  'approver_id': 'Zatwierdzający',
  'verifier_id': 'Weryfikujący',
  'window_start': 'Okno od',
  'window_end': 'Okno do',
  'ci_ids': 'Obiekty (CI)',
  'status': 'Status',
  'number': 'Numer',
  'requested_by_id': 'Zgłaszający',
  'approved_at': 'Zatwierdzono',
  'approved_by_id': 'Zatwierdził',
  'implemented_at': 'Wdrożono',
  'verified_at': 'Zweryfikowano',
  'rejected_at': 'Odrzucono',
  'consent_round': 'Runda zgód',
  'supersedes_change_id': 'Korekta zmiany',
  'version': 'Wersja',
  // other audited entities (log browser, ADR 0015)
  'name': 'Nazwa',
  'prefix': 'Prefiks',
  'tax_id': 'NIP',
  'is_ksc_entity': 'Podmiot uoKSC',
  'default_approver_id': 'Domyślny zatwierdzający',
  'roles': 'Role',
  'is_active': 'Aktywny',
  'identifier': 'Identyfikator',
  'ci_type_id': 'Typ obiektu',
  'owner_user_id': 'Właściciel',
  'code': 'Kod',
  'parent_id': 'Kategoria nadrzędna',
  'requires_approval': 'Wymaga zatwierdzenia',
  'requires_ci_owner_consent': 'Zgoda właściciela CI',
  'default_risk': 'Domyślne ryzyko',
  'email': 'E-mail',
  'display_name': 'Nazwa wyświetlana',
  'approver_override_id': 'Zatwierdzający kategorii',
  'external_id': 'Identyfikator konta (IdP)',
  'is_app_admin': 'Administrator aplikacji',
};

String fieldLabel(String field) => changeFieldLabels[field] ?? field;

/// Change actions (`POST …/actions/{action}`) with labels and rules for the
/// confirmation dialog. Which actions are offered comes ONLY from the API
/// (`allowed_actions`); this table only describes them.
abstract final class ChangeActions {
  static const List<String> order = [
    'submit',
    'approve',
    'implement',
    'verify',
    'consent',
    'return',
    'reject',
    'rollback',
    'cancel',
  ];

  static String label(String action, Change change) => switch (action) {
    'submit' => 'Wyślij do zatwierdzenia',
    'return' => 'Zwróć do poprawy',
    'approve' =>
      change.status == ChangeStatus.implemented.apiValue
          ? 'Zatwierdź po fakcie'
          : 'Zatwierdź',
    'reject' => 'Odrzuć',
    'implement' =>
      change.status == ChangeStatus.draft.apiValue
          ? 'Wdróż awaryjnie'
          : 'Oznacz jako wdrożoną',
    'verify' => 'Potwierdź weryfikację',
    'rollback' => 'Wycofaj',
    'cancel' => 'Anuluj zmianę',
    'consent' => 'Wyraź zgodę (właściciel CI)',
    _ => action,
  };

  static String description(String action, Change change) => switch (action) {
    'submit' =>
      'Zmiana trafi do zatwierdzającego. Zmiana standardowa w kategorii bez '
          'wymogu zatwierdzenia zostanie zatwierdzona automatycznie.',
    'return' => 'Zmiana wróci do autora jako szkic. Podaj, co poprawić.',
    'approve' =>
      change.status == ChangeStatus.implemented.apiValue
          ? 'Zatwierdzasz po fakcie wdrożoną zmianę awaryjną.'
          : 'Zatwierdzasz zmianę w wersji, którą widzisz na karcie.',
    'reject' => 'Zmiana zostanie odrzucona (stan końcowy). Podaj powód.',
    'implement' =>
      change.status == ChangeStatus.draft.apiValue
          ? 'Zmiana awaryjna zostanie oznaczona jako wdrożona przed '
                'zatwierdzeniem. Zatwierdzenie po fakcie jest wymagane w '
                'ciągu 24 h.'
          : 'Potwierdzasz, że zmiana została wdrożona. Od tej chwili karta '
                'jest zamrożona.',
    'verify' => 'Potwierdzasz, że zmiana działa zgodnie z planem.',
    'rollback' => 'Zmiana zostanie oznaczona jako wycofana. Podaj powód.',
    'cancel' => 'Zmiana zostanie anulowana (stan końcowy).',
    'consent' =>
      'Jako właściciel obiektu (CI) wyrażasz zgodę na tę zmianę dla swoich '
          'obiektów.',
    _ => '',
  };

  /// Noun for the action a comment was given with ("Odrzucenie").
  static String noun(String action) => switch (action) {
    'submit' => 'Wysłanie',
    'return' => 'Zwrot do poprawy',
    'approve' => 'Zatwierdzenie',
    'reject' => 'Odrzucenie',
    'implement' => 'Wdrożenie',
    'verify' => 'Weryfikacja',
    'rollback' => 'Wycofanie',
    'cancel' => 'Anulowanie',
    'consent' => 'Zgoda właściciela CI',
    _ => action,
  };

  /// Comment required by the state machine (ADR 0012 §2).
  static bool commentRequired(String action, Change change) => switch (action) {
    'return' || 'reject' || 'rollback' => true,
    'cancel' => change.status != ChangeStatus.draft.apiValue,
    _ => false,
  };

  /// Destructive / negative actions (styled as such).
  static bool isNegative(String action) =>
      const {'return', 'reject', 'rollback', 'cancel'}.contains(action);

  static const int maxCommentLength = 4000;
}

/// Polish phrase for an audit entry ("— zatwierdził(a)").
String auditActionPhrase(AuditEntry entry) {
  final context = entry.context;
  String? filename() => context['filename'] as String?;
  switch (entry.action) {
    case 'create':
      return entry.entityType == 'attachment'
          ? 'dodał(a) załącznik'
          : 'utworzył(a) zmianę';
    case 'update':
      return 'zmienił(a) dane zmiany';
    case 'comment':
      return 'dodał(a) komentarz';
    case 'attach':
      final name = filename();
      return name == null ? 'dodał(a) załącznik' : 'dodał(a) załącznik $name';
    case 'download':
      final name = filename();
      return name == null ? 'pobrał(a) załącznik' : 'pobrał(a) załącznik $name';
    case 'transition':
      final action = context['action'] as String?;
      final same = context['from_status'] == context['to_status'];
      return switch (action) {
        'submit' when context['auto_approved'] == true =>
          'zatwierdził automatycznie (zmiana standardowa)',
        'submit' => 'wysłał(a) do zatwierdzenia',
        'return' => 'zwrócił(a) do poprawy',
        'approve' when same => 'zatwierdził(a) po fakcie',
        'approve' => 'zatwierdził(a)',
        'reject' => 'odrzucił(a)',
        'implement' => 'oznaczył(a) jako wdrożoną',
        'verify' => 'potwierdził(a) weryfikację',
        'rollback' => 'wycofał(a)',
        'cancel' => 'anulował(a)',
        'consent' => 'wyraził(a) zgodę właściciela CI',
        _ => 'zmienił(a) status',
      };
    default:
      return entry.action;
  }
}

/// Names of ids appearing in diffs (users, categories, CI).
class NameResolver {
  NameResolver({
    Map<String, String> users = const {},
    Map<String, String> categories = const {},
    Map<String, String> cis = const {},
  }) : _users = Map.unmodifiable(users),
       _categories = Map.unmodifiable(categories),
       _cis = Map.unmodifiable(cis);

  /// Everything referenced by a change card.
  factory NameResolver.forChange(
    Change change, {
    List<Member> members = const [],
    List<CompanyCategory> categories = const [],
  }) {
    final users = <String, String>{
      for (final m in members) m.userId: m.displayName,
    };
    void add(UserRef? ref) {
      if (ref != null) users[ref.id] = ref.displayName;
    }

    add(change.requestedBy);
    add(change.assignee);
    add(change.approver);
    add(change.verifier);
    add(change.approvedBy);
    for (final c in change.comments) {
      add(c.author);
    }
    for (final c in change.consents) {
      add(c.owner);
    }
    for (final ci in change.ci) {
      add(ci.owner);
    }
    return NameResolver(
      users: users,
      categories: {
        for (final c in categories) c.categoryId: c.name,
        if (change.category != null) change.category!.id: change.category!.name,
        if (change.subcategory != null)
          change.subcategory!.id: change.subcategory!.name,
      },
      cis: {for (final ci in change.ci) ci.id: ci.identifier},
    );
  }

  final Map<String, String> _users;
  final Map<String, String> _categories;
  final Map<String, String> _cis;

  static String shortId(String id) =>
      id.length > 8 ? '${id.substring(0, 8)}…' : id;

  String user(String id) => _users[id] ?? shortId(id);
  String category(String id) => _categories[id] ?? shortId(id);
  String ci(String id) => _cis[id] ?? shortId(id);

  /// Display value of [field] in an audit diff.
  String value(String field, Object? value) {
    if (value == null) return '—';
    if (value is List) {
      if (value.isEmpty) return '—';
      return value.map((v) => this.value(field, v)).join(', ');
    }
    final text = '$value';
    switch (field) {
      case 'status':
        return ChangeStatus.tryParse(text)?.label ?? text;
      case 'change_type':
        return ChangeTypes.label(text);
      case 'risk':
        return Risks.label(text);
      case 'assignee_id':
      case 'approver_id':
      case 'verifier_id':
      case 'requested_by_id':
      case 'approved_by_id':
        return user(text);
      case 'category_id':
      case 'subcategory_id':
        return category(text);
      case 'ci_ids':
        return ci(text);
      case 'window_start':
      case 'window_end':
      case 'approved_at':
      case 'implemented_at':
      case 'verified_at':
      case 'rejected_at':
        final parsed = parseApiDateTime(text);
        return parsed == null ? text : WarsawTime.format(parsed);
      default:
        return text;
    }
  }
}

/// Fields whose values are identifiers/dates (rendered in the mono font).
bool isMonoField(String field) => const {
  'number',
  'window_start',
  'window_end',
  'approved_at',
  'implemented_at',
  'verified_at',
  'rejected_at',
  'ci_ids',
  'ticket_ref',
  'version',
  'consent_round',
}.contains(field);

/// Audit actor: "Ewa Edytorska (Edytor)" or "system".
String auditActor(AuditEntry entry) {
  if (entry.actorId == null) return 'system';
  final roles = entry.actorRoles.map(Roles.label).join(', ');
  return roles.isEmpty ? entry.actorDisplay : '${entry.actorDisplay} ($roles)';
}
