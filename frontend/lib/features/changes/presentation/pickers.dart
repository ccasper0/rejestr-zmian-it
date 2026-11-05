import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme.dart';
import '../../../core/time.dart';
import '../../../widgets/common.dart';
import '../data/changes_api.dart';
import '../data/models.dart';

/// Filter button of the register bar: "Status: Szkic +1" with a clear icon.
class FilterButton extends StatelessWidget {
  const FilterButton({
    required this.label,
    required this.value,
    required this.onPressed,
    this.onClear,
    super.key,
  });

  final String label;

  /// Current value summary; empty = filter not set.
  final String value;
  final VoidCallback onPressed;
  final VoidCallback? onClear;

  @override
  Widget build(BuildContext context) {
    final active = value.isNotEmpty;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        OutlinedButton(
          onPressed: onPressed,
          style: OutlinedButton.styleFrom(
            side: BorderSide(
              color: active ? AppColors.accent : AppColors.border,
              width: active ? 1.5 : 1,
            ),
            backgroundColor: active
                ? AppStatusColors.approved.background
                : AppColors.surface,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(active ? '$label: $value' : label),
              const SizedBox(width: 4),
              const Icon(Icons.arrow_drop_down, size: 20),
            ],
          ),
        ),
        if (active && onClear != null)
          IconButton(
            tooltip: 'Wyczyść filtr: $label',
            onPressed: onClear,
            icon: const Icon(Icons.close, size: 18),
          ),
      ],
    );
  }
}

/// Result of a single-select dialog ([value] null = "any / none").
class Picked {
  const Picked(this.value);

  final String? value;
}

Future<List<String>?> showMultiSelectDialog(
  BuildContext context, {
  required String title,
  required List<(String, String)> options,
  required List<String> selected,
}) {
  final current = {...selected};
  return showDialog<List<String>>(
    context: context,
    builder: (context) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: 360,
          child: options.isEmpty
              ? const Text('Brak opcji.')
              : ListView(
                  shrinkWrap: true,
                  children: [
                    for (final (value, label) in options)
                      CheckboxListTile(
                        value: current.contains(value),
                        title: Text(label),
                        controlAffinity: ListTileControlAffinity.leading,
                        onChanged: (checked) => setState(() {
                          if (checked ?? false) {
                            current.add(value);
                          } else {
                            current.remove(value);
                          }
                        }),
                      ),
                  ],
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, [
              for (final (value, _) in options)
                if (current.contains(value)) value,
              // keep selected values not present in options (e.g. stale ids)
              for (final value in current)
                if (!options.any((o) => o.$1 == value)) value,
            ]),
            child: const Text('Zastosuj'),
          ),
        ],
      ),
    ),
  );
}

Future<Picked?> showSingleSelectDialog(
  BuildContext context, {
  required String title,
  required List<(String, String)> options,
  required String? selected,
  String anyLabel = 'Wszyscy',
}) {
  return showDialog<Picked>(
    context: context,
    builder: (context) => SimpleDialog(
      title: Text(title),
      children: [
        RadioGroup<String?>(
          groupValue: selected,
          onChanged: (value) => Navigator.pop(context, Picked(value)),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              RadioListTile<String?>(value: null, title: Text(anyLabel)),
              for (final (value, label) in options)
                RadioListTile<String?>(value: value, title: Text(label)),
            ],
          ),
        ),
      ],
    ),
  );
}

/// Register period: Warsaw calendar days `yyyy-MM-dd` (both inclusive).
Future<(String, String)?> pickPeriod(
  BuildContext context,
  String? from,
  String? to,
) async {
  DateTime? local(String? iso) {
    final instant = WarsawTime.startOfIsoDay(iso);
    if (instant == null) return null;
    final w = WarsawTime.toWarsaw(instant);
    return DateTime(w.year, w.month, w.day);
  }

  final now = WarsawTime.toWarsaw(DateTime.now());
  final start = local(from);
  final end = local(to);
  final range = await showDateRangePicker(
    context: context,
    firstDate: DateTime(2000),
    lastDate: DateTime(now.year + 5, 12, 31),
    initialDateRange: start != null && end != null && !end.isBefore(start)
        ? DateTimeRange(start: start, end: end)
        : null,
    helpText: 'Okres',
    saveText: 'Zastosuj',
  );
  if (range == null) return null;
  String iso(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';
  return (iso(range.start), iso(range.end));
}

/// Picks a Warsaw wall-clock date and time; returns the instant (UTC).
Future<DateTime?> pickWarsawDateTime(
  BuildContext context, {
  DateTime? initial,
}) async {
  final base = WarsawTime.toWarsaw(initial ?? DateTime.now());
  final date = await showDatePicker(
    context: context,
    initialDate: DateTime(base.year, base.month, base.day),
    firstDate: DateTime(2000),
    lastDate: DateTime(base.year + 5, 12, 31),
    helpText: 'Data (czas polski)',
  );
  if (date == null || !context.mounted) return null;
  final time = await showTimePicker(
    context: context,
    initialTime: TimeOfDay(hour: base.hour, minute: base.minute),
    helpText: 'Godzina (czas polski)',
    builder: (context, child) => MediaQuery(
      data: MediaQuery.of(context).copyWith(alwaysUse24HourFormat: true),
      child: child!,
    ),
  );
  if (time == null) return null;
  return WarsawTime.fromWarsaw(
    date.year,
    date.month,
    date.day,
    time.hour,
    time.minute,
  );
}

/// CI filter: search the company's inventory and tick objects.
Future<List<String>?> showCiFilterDialog(
  BuildContext context, {
  required String companyId,
  required List<String> selected,
}) => showDialog<List<String>>(
  context: context,
  builder: (_) => _CiFilterDialog(companyId: companyId, selected: selected),
);

class _CiFilterDialog extends ConsumerStatefulWidget {
  const _CiFilterDialog({required this.companyId, required this.selected});

  final String companyId;
  final List<String> selected;

  @override
  ConsumerState<_CiFilterDialog> createState() => _CiFilterDialogState();
}

class _CiFilterDialogState extends ConsumerState<_CiFilterDialog> {
  late final Set<String> _selected = {...widget.selected};
  final Map<String, CiItem> _known = {};
  List<CiItem> _results = const [];
  Object? _error;
  bool _loading = true;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _search('');
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _search(String q) async {
    setState(() => _loading = true);
    try {
      final page = await ref
          .read(changesApiProvider)
          .listCi(widget.companyId, q: q, limit: 100);
      if (!mounted) return;
      setState(() {
        _results = page.items;
        for (final item in page.items) {
          _known[item.id] = item;
        }
        _error = null;
      });
    } on Object catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Obiekt (CI)'),
      content: SizedBox(
        width: 440,
        height: 420,
        child: Column(
          children: [
            TextField(
              autofocus: true,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Identyfikator lub nazwa',
                isDense: true,
              ),
              onChanged: (value) {
                _debounce?.cancel();
                _debounce = Timer(
                  const Duration(milliseconds: 300),
                  () => _search(value),
                );
              },
            ),
            const SizedBox(height: 8),
            if (_loading) const LinearProgressIndicator(minHeight: 2),
            if (_error != null) ErrorPanel(error: _error!),
            Expanded(
              child: ListView(
                children: [
                  for (final item in _results)
                    CheckboxListTile(
                      value: _selected.contains(item.id),
                      controlAffinity: ListTileControlAffinity.leading,
                      title: Text(
                        item.identifier,
                        style: AppFonts.monoStyle(fontSize: 14),
                      ),
                      subtitle: Text(
                        item.isActive ? item.name : '${item.name} (nieaktywny)',
                      ),
                      onChanged: (checked) => setState(() {
                        if (checked ?? false) {
                          _selected.add(item.id);
                        } else {
                          _selected.remove(item.id);
                        }
                      }),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Anuluj'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, _selected.toList()),
          child: const Text('Zastosuj'),
        ),
      ],
    );
  }
}
