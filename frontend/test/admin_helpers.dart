import 'helpers.dart';

// UUIDs: the user detail route validates its parameter (ADR 0014 §13 pt 3).
const adminId = '00000000-0000-4000-8000-000000000001';
const editorUuid = '00000000-0000-4000-8000-000000000002';
const approverUuid = '00000000-0000-4000-8000-000000000003';
const companyDelta = 'c-delta';

Map<String, Object?> adminMe({List<String> alfaRoles = const []}) => meJson(
  id: adminId,
  name: 'Adam Administrator',
  admin: true,
  alfaRoles: alfaRoles,
  betaRoles: const [],
);

Map<String, Object?> companyJson({
  String id = companyAlfa,
  String name = 'Alfa S.A.',
  String prefix = 'ALFA',
  String status = 'active',
  String? taxId = '5260250995',
  bool ksc = true,
  String? defaultApproverId,
  List<String> myRoles = const [],
  Map<String, int> counts = const {
    'active_ci': 12,
    'all_ci': 13,
    'editors': 2,
    'approvers': 1,
    'auditors': 1,
    'viewers': 1,
  },
}) => {
  'id': id,
  'name': name,
  'tax_id': taxId,
  'prefix': prefix,
  'status': status,
  'is_ksc_entity': ksc,
  'default_approver_id': defaultApproverId,
  'created_at': '2026-10-28T08:00:00Z',
  'updated_at': '2026-10-28T08:00:00Z',
  'my_roles': myRoles,
  'counts': counts,
};

Map<String, Object?> categoryJson({
  required String id,
  required String code,
  required String name,
  String? parentId,
  bool requiresApproval = true,
  bool consent = false,
  String risk = 'medium',
  bool active = true,
}) => {
  'id': id,
  'code': code,
  'name': name,
  'parent_id': parentId,
  'requires_approval': requiresApproval,
  'requires_ci_owner_consent': consent,
  'default_risk': risk,
  'is_active': active,
  'created_at': '2026-10-28T08:00:00Z',
  'updated_at': '2026-10-28T08:00:00Z',
};

Map<String, Object?> userJson(
  String id,
  String name, {
  bool admin = false,
  bool active = true,
}) => {
  'id': id,
  'external_id': 'dev-$name',
  'email': '${name.split(' ').first.toLowerCase()}@example.com',
  'display_name': name,
  'is_app_admin': admin,
  'is_active': active,
  'created_at': '2026-10-28T08:00:00Z',
  'updated_at': '2026-10-28T08:00:00Z',
};

final List<Map<String, Object?>> dictionary = [
  categoryJson(
    id: 'cat-acc',
    code: 'ACC',
    name: 'Konta i uprawnienia',
    requiresApproval: false,
    risk: 'low',
  ),
  categoryJson(
    id: 'cat-acc-priv',
    code: 'ACC-PRIV',
    name: 'Konto uprzywilejowane',
    parentId: 'cat-acc',
  ),
  categoryJson(id: 'cat-fw', code: 'FW', name: 'Firewall / sieć'),
  categoryJson(
    id: 'cat-fw-nat',
    code: 'FW-NAT',
    name: 'NAT',
    parentId: 'cat-fw',
    active: false,
    requiresApproval: false,
  ),
  categoryJson(
    id: 'cat-ot',
    code: 'OT',
    name: 'Systemy OT',
    consent: true,
    risk: 'high',
  ),
  categoryJson(id: 'cat-old', code: 'OLD', name: 'Wycofana', active: false),
];

extension FakeApiAdmin on FakeApi {
  /// Admin without memberships + admin endpoints.
  void installAdmin({Map<String, Object?>? me}) {
    installDefaults(me: me ?? adminMe());
    reply(
      'GET',
      '/companies',
      page([
        companyJson(),
        companyJson(
          id: companyBeta,
          name: 'Beta sp. z o.o.',
          prefix: 'BETA',
          status: 'archived',
          taxId: null,
          ksc: false,
          counts: const {
            'active_ci': 7,
            'all_ci': 8,
            'editors': 3,
            'approvers': 2,
            'auditors': 0,
            'viewers': 0,
          },
        ),
      ]),
    );
    reply('GET', '/categories', page(dictionary));
    reply(
      'GET',
      '/users',
      page([
        userJson(adminId, 'Adam Administrator', admin: true),
        userJson(editorUuid, 'Ewa Edytorska'),
        userJson(approverUuid, 'Jan Zatwierdzający'),
      ]),
    );
    reply('GET', '/companies/[^/]+/categories', {'items': <Object?>[]});
    reply('GET', '/companies/[^/]+/members', page([]));
  }
}
