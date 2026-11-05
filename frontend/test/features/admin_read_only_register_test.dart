// ADR 0016: the app admin without a role in a company reads its change
// register and cards on the API's read-only path — no writes, no actions,
// no attachment download (only the name, size and sha256).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rejestr_zmian/widgets/company_scope.dart';

import '../admin_helpers.dart';
import '../helpers.dart';

const _wide = Size(1500, 1400);
const _number = 'CHG-ALFA-2026-0001';
const _cardPath = '/c/ALFA/changes/$_number';
const _byNumber = '/companies/c-alfa/changes/by-number/$_number';
const _sha = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';

Map<String, Object?> _attachment() => {
  'id': 'att-1',
  'change_id': 'ch-1',
  'filename': 'protokol.txt',
  'content_type': 'text/plain',
  'size': 2048,
  'sha256': _sha,
  'uploaded_by': userRef(userEditor, 'Ewa Edytorska'),
  'created_at': '2026-10-29T09:00:00Z',
};

/// A card as the API returns it to the admin without a role.
Map<String, Object?> _adminCard({
  List<String> allowedActions = const [],
  List<String> editableFields = const [],
}) => changeJson(
  status: 'implemented',
  access: 'admin_read_only',
  allowedActions: allowedActions,
  editableFields: editableFields,
);

FakeApi _adminApi(Map<String, Object?> card) => FakeApi()
  ..installAdmin()
  ..reply('GET', '/companies/c-alfa/changes', page([changeJson()]))
  ..reply('GET', _byNumber, card)
  ..reply('GET', '/companies/c-alfa/changes/ch-1/attachments', [_attachment()]);

Finder _anyAction() => find.byWidgetPredicate((w) {
  final key = w.key;
  return key is ValueKey<String> && key.value.startsWith('action-');
});

void main() {
  group('app admin without a role', () {
    testWidgets('register: rows, tiles and a read-only banner, no "Nowa '
        'zmiana"', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _adminApi(_adminCard());
      await pumpApp(tester, api: api, location: '/c/ALFA/changes');

      expect(find.byKey(const ValueKey('no-access')), findsNothing);
      expect(find.byKey(const ValueKey('admin-read-only')), findsOneWidget);
      expect(find.text(AdminReadOnlyBanner.title), findsOneWidget);
      expect(find.text(_number), findsOneWidget);
      expect(find.byKey(const ValueKey('tile-pending')), findsOneWidget);
      expect(find.byKey(const ValueKey('new-change')), findsNothing);
      expect(api.calls('GET', '/companies/c-alfa/changes'), isNotEmpty);
      expect(api.calls('GET', '/companies/c-alfa/stats'), isNotEmpty);
      // the approver's work queue is not offered on the admin path
      expect(find.text('Do zatwierdzenia'), findsOneWidget); // the tile only
      expect(find.text('Rejestr zmian'), findsWidgets);
    });

    testWidgets('card: banner, no edit, actions, comments, upload or '
        'download; attachment metadata with full sha256', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _adminApi(_adminCard());
      await pumpApp(tester, api: api, location: _cardPath);

      expect(find.byKey(const ValueKey('no-access')), findsNothing);
      expect(find.byKey(const ValueKey('admin-read-only')), findsOneWidget);
      expect(find.text('Aktualizacja reguł zapory'), findsOneWidget);
      expect(_anyAction(), findsNothing);
      expect(find.byKey(const ValueKey('card-edit')), findsNothing);
      expect(find.byKey(const ValueKey('comment-field')), findsNothing);
      expect(find.byKey(const ValueKey('comment-send')), findsNothing);
      expect(find.byKey(const ValueKey('attachment-upload')), findsNothing);
      expect(
        find.byKey(const ValueKey('attachment-download-att-1')),
        findsNothing,
      );
      expect(find.byIcon(Icons.download_outlined), findsNothing);
      expect(find.text('protokol.txt'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('attachment-sha256-att-1')),
        findsOneWidget,
      );
      expect(find.text('sha256 $_sha'), findsOneWidget);
      // the read paths of ADR 0016 §2 are used, nothing else
      expect(
        api.calls('GET', '/companies/c-alfa/changes/ch-1/attachments'),
        isNotEmpty,
      );
      expect(
        api.calls('GET', '/companies/c-alfa/changes/ch-1/attachments/.+'),
        isEmpty,
      );
      expect(
        api.requests.where((r) => r.method != 'GET' && r.method != 'HEAD'),
        isEmpty,
      );
    });

    testWidgets('card stays read-only even if lists are not empty', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(
        tester,
        api: _adminApi(
          _adminCard(
            allowedActions: ['verify', 'rollback'],
            editableFields: ['verifier_id'],
          ),
        ),
        location: _cardPath,
      );

      expect(find.byKey(const ValueKey('admin-read-only')), findsOneWidget);
      expect(_anyAction(), findsNothing);
      expect(find.byKey(const ValueKey('card-edit')), findsNothing);
    });

    testWidgets('new change and edit form: "Brak dostępu", no request', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _adminApi(_adminCard());
      final router = await pumpApp(
        tester,
        api: api,
        location: '/c/ALFA/changes/new',
      );
      expect(find.byKey(const ValueKey('no-access')), findsOneWidget);
      expect(find.textContaining('rozdział obowiązków'), findsOneWidget);
      expect(api.calls('POST', '/companies/.*/changes'), isEmpty);

      // the banner leads to the read-only register
      await tester.tap(find.byKey(const ValueKey('no-access-register')));
      await tester.pumpAndSettle();
      expect(currentPath(router), '/c/ALFA/changes');
      expect(find.byKey(const ValueKey('admin-read-only')), findsOneWidget);
    });

    testWidgets('edit form: "Brak dostępu", no card request', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = _adminApi(_adminCard());
      await pumpApp(tester, api: api, location: '$_cardPath/edit');
      expect(find.byKey(const ValueKey('no-access')), findsOneWidget);
      expect(api.calls('GET', _byNumber), isEmpty);
    });

    testWidgets('side panel hides "Do zatwierdzenia"', (tester) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(
        tester,
        api: _adminApi(_adminCard()),
        location: '/c/ALFA/ci',
      );
      expect(find.text('Rejestr zmian'), findsOneWidget);
      expect(find.text('Do zatwierdzenia'), findsNothing);
      expect(find.text('Obiekty (CI)'), findsWidgets);
    });

    testWidgets('unknown company: not found, no register request', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = _adminApi(_adminCard());
      await pumpApp(tester, api: api, location: '/c/ZETA/changes');
      expect(find.text('Nie znaleziono spółki.'), findsOneWidget);
      expect(api.calls('GET', '/companies/.*/changes'), isEmpty);
    });
  });

  group('members keep their behaviour', () {
    testWidgets('editor: no banner, "Nowa zmiana", approvals link', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      await pumpApp(tester, location: '/c/ALFA/changes');
      expect(find.byKey(const ValueKey('admin-read-only')), findsNothing);
      expect(find.byKey(const ValueKey('new-change')), findsOneWidget);
      // side panel link + tile
      expect(find.text('Do zatwierdzenia'), findsNWidgets(2));
    });

    testWidgets('admin with a role is resolved by that role', (tester) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()
        ..installAdmin(me: adminMe(alfaRoles: ['editor']))
        ..reply('GET', _byNumber, changeJson())
        ..reply('GET', '/companies/c-alfa/changes/ch-1/attachments', [
          _attachment(),
        ]);
      await pumpApp(tester, api: api, location: _cardPath);
      expect(find.byKey(const ValueKey('admin-read-only')), findsNothing);
      expect(find.byKey(const ValueKey('card-edit')), findsOneWidget);
      expect(find.byKey(const ValueKey('action-submit')), findsOneWidget);
    });

    testWidgets('editor card: download, upload and comments available', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()
        ..installDefaults()
        ..reply('GET', _byNumber, changeJson())
        ..reply('GET', '/companies/c-alfa/changes/ch-1/attachments', [
          _attachment(),
        ]);
      await pumpApp(tester, api: api, location: _cardPath);

      expect(find.byKey(const ValueKey('admin-read-only')), findsNothing);
      expect(
        find.byKey(const ValueKey('attachment-download-att-1')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('attachment-sha256-att-1')),
        findsNothing,
      );
      expect(find.byKey(const ValueKey('attachment-upload')), findsOneWidget);
      expect(find.byKey(const ValueKey('comment-field')), findsOneWidget);
    });

    testWidgets('viewer card: download yes, upload and comments no', (
      tester,
    ) async {
      setSurfaceSize(tester, _wide);
      final api = FakeApi()
        ..installDefaults(
          me: meJson(alfaRoles: ['viewer'], betaRoles: []),
        )
        ..reply(
          'GET',
          _byNumber,
          changeJson(status: 'approved', allowedActions: const []),
        )
        ..reply('GET', '/companies/c-alfa/changes/ch-1/attachments', [
          _attachment(),
        ]);
      await pumpApp(tester, api: api, location: _cardPath);

      expect(find.byKey(const ValueKey('admin-read-only')), findsNothing);
      expect(
        find.byKey(const ValueKey('attachment-download-att-1')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('attachment-upload')), findsNothing);
      expect(find.byKey(const ValueKey('comment-field')), findsNothing);
    });
  });
}
