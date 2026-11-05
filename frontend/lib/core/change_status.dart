/// Change lifecycle statuses (CLAUDE.md, section 4.2).
///
/// The frontend only *displays* statuses — transitions are performed by the
/// backend via `POST .../actions/{action}`.
enum ChangeStatus {
  draft('draft', 'Szkic'),
  pendingApproval('pending_approval', 'Do zatwierdzenia'),
  approved('approved', 'Zatwierdzona'),
  implemented('implemented', 'Wdrożona'),
  verified('verified', 'Zweryfikowana'),
  rejected('rejected', 'Odrzucona'),
  rolledBack('rolled_back', 'Wycofana'),
  cancelled('cancelled', 'Anulowana');

  const ChangeStatus(this.apiValue, this.label);

  /// Value used by the API (snake_case).
  final String apiValue;

  /// Polish UI label.
  final String label;

  static ChangeStatus? tryParse(String? value) {
    for (final status in values) {
      if (status.apiValue == value) return status;
    }
    return null;
  }
}
