// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'report_form.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$ReportForm {

 String? get from; String? get to; String get periodBy; List<String> get statuses; List<String> get types; List<String> get categories; List<String> get cis; String? get assignee; String? get approvedBy; String get q; bool get includeAuditTrail;
/// Create a copy of ReportForm
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ReportFormCopyWith<ReportForm> get copyWith => _$ReportFormCopyWithImpl<ReportForm>(this as ReportForm, _$identity);



@override
bool operator ==(Object other) {
  final _this = this as ReportForm;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ReportForm&&(identical(other.from, _this.from) || other.from == _this.from)&&(identical(other.to, _this.to) || other.to == _this.to)&&(identical(other.periodBy, _this.periodBy) || other.periodBy == _this.periodBy)&&const DeepCollectionEquality().equals(other.statuses, _this.statuses)&&const DeepCollectionEquality().equals(other.types, _this.types)&&const DeepCollectionEquality().equals(other.categories, _this.categories)&&const DeepCollectionEquality().equals(other.cis, _this.cis)&&(identical(other.assignee, _this.assignee) || other.assignee == _this.assignee)&&(identical(other.approvedBy, _this.approvedBy) || other.approvedBy == _this.approvedBy)&&(identical(other.q, _this.q) || other.q == _this.q)&&(identical(other.includeAuditTrail, _this.includeAuditTrail) || other.includeAuditTrail == _this.includeAuditTrail));
}


@override
int get hashCode {
  final _this = this as ReportForm;
  return Object.hash(runtimeType,_this.from,_this.to,_this.periodBy,const DeepCollectionEquality().hash(_this.statuses),const DeepCollectionEquality().hash(_this.types),const DeepCollectionEquality().hash(_this.categories),const DeepCollectionEquality().hash(_this.cis),_this.assignee,_this.approvedBy,_this.q,_this.includeAuditTrail);
}

@override
String toString() {
  final _this = this as ReportForm;
  return 'ReportForm(from: ${_this.from}, to: ${_this.to}, periodBy: ${_this.periodBy}, statuses: ${_this.statuses}, types: ${_this.types}, categories: ${_this.categories}, cis: ${_this.cis}, assignee: ${_this.assignee}, approvedBy: ${_this.approvedBy}, q: ${_this.q}, includeAuditTrail: ${_this.includeAuditTrail})';
}


}

/// @nodoc
abstract mixin class $ReportFormCopyWith<$Res>  {
  factory $ReportFormCopyWith(ReportForm value, $Res Function(ReportForm) _then) = _$ReportFormCopyWithImpl;
@useResult
$Res call({
 String? from, String? to, String periodBy, List<String> statuses, List<String> types, List<String> categories, List<String> cis, String? assignee, String? approvedBy, String q, bool includeAuditTrail
});




}
/// @nodoc
class _$ReportFormCopyWithImpl<$Res>
    implements $ReportFormCopyWith<$Res> {
  _$ReportFormCopyWithImpl(this._self, this._then);

  final ReportForm _self;
  final $Res Function(ReportForm) _then;

/// Create a copy of ReportForm
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? from = freezed,Object? to = freezed,Object? periodBy = null,Object? statuses = null,Object? types = null,Object? categories = null,Object? cis = null,Object? assignee = freezed,Object? approvedBy = freezed,Object? q = null,Object? includeAuditTrail = null,}) {
  return _then(ReportForm(
from: freezed == from ? _self.from : from // ignore: cast_nullable_to_non_nullable
as String?,to: freezed == to ? _self.to : to // ignore: cast_nullable_to_non_nullable
as String?,periodBy: null == periodBy ? _self.periodBy : periodBy // ignore: cast_nullable_to_non_nullable
as String,statuses: null == statuses ? _self.statuses : statuses // ignore: cast_nullable_to_non_nullable
as List<String>,types: null == types ? _self.types : types // ignore: cast_nullable_to_non_nullable
as List<String>,categories: null == categories ? _self.categories : categories // ignore: cast_nullable_to_non_nullable
as List<String>,cis: null == cis ? _self.cis : cis // ignore: cast_nullable_to_non_nullable
as List<String>,assignee: freezed == assignee ? _self.assignee : assignee // ignore: cast_nullable_to_non_nullable
as String?,approvedBy: freezed == approvedBy ? _self.approvedBy : approvedBy // ignore: cast_nullable_to_non_nullable
as String?,q: null == q ? _self.q : q // ignore: cast_nullable_to_non_nullable
as String,includeAuditTrail: null == includeAuditTrail ? _self.includeAuditTrail : includeAuditTrail // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [ReportForm].
extension ReportFormPatterns on ReportForm {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ReportForm value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ReportForm() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ReportForm value)  $default,){
final _that = this;
switch (_that) {
case _ReportForm():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ReportForm value)?  $default,){
final _that = this;
switch (_that) {
case _ReportForm() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String? from,  String? to,  String periodBy,  List<String> statuses,  List<String> types,  List<String> categories,  List<String> cis,  String? assignee,  String? approvedBy,  String q,  bool includeAuditTrail)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ReportForm() when $default != null:
return $default(_that.from,_that.to,_that.periodBy,_that.statuses,_that.types,_that.categories,_that.cis,_that.assignee,_that.approvedBy,_that.q,_that.includeAuditTrail);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String? from,  String? to,  String periodBy,  List<String> statuses,  List<String> types,  List<String> categories,  List<String> cis,  String? assignee,  String? approvedBy,  String q,  bool includeAuditTrail)  $default,) {final _that = this;
switch (_that) {
case _ReportForm():
return $default(_that.from,_that.to,_that.periodBy,_that.statuses,_that.types,_that.categories,_that.cis,_that.assignee,_that.approvedBy,_that.q,_that.includeAuditTrail);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String? from,  String? to,  String periodBy,  List<String> statuses,  List<String> types,  List<String> categories,  List<String> cis,  String? assignee,  String? approvedBy,  String q,  bool includeAuditTrail)?  $default,) {final _that = this;
switch (_that) {
case _ReportForm() when $default != null:
return $default(_that.from,_that.to,_that.periodBy,_that.statuses,_that.types,_that.categories,_that.cis,_that.assignee,_that.approvedBy,_that.q,_that.includeAuditTrail);case _:
  return null;

}
}

}

/// @nodoc


class _ReportForm extends ReportForm {
  const _ReportForm({this.from, this.to, this.periodBy = RegisterFilters.defaultPeriodBy,  List<String> statuses = const <String>[],  List<String> types = const <String>[],  List<String> categories = const <String>[],  List<String> cis = const <String>[], this.assignee, this.approvedBy, this.q = '', this.includeAuditTrail = false}): _statuses = statuses,_types = types,_categories = categories,_cis = cis,super._();
  

@override final  String? from;
@override final  String? to;
@override@JsonKey() final  String periodBy;
 final  List<String> _statuses;
@override@JsonKey() List<String> get statuses {
  if (_statuses is EqualUnmodifiableListView) return _statuses;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_statuses);
}

 final  List<String> _types;
@override@JsonKey() List<String> get types {
  if (_types is EqualUnmodifiableListView) return _types;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_types);
}

 final  List<String> _categories;
@override@JsonKey() List<String> get categories {
  if (_categories is EqualUnmodifiableListView) return _categories;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_categories);
}

 final  List<String> _cis;
@override@JsonKey() List<String> get cis {
  if (_cis is EqualUnmodifiableListView) return _cis;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_cis);
}

@override final  String? assignee;
@override final  String? approvedBy;
@override@JsonKey() final  String q;
@override@JsonKey() final  bool includeAuditTrail;

/// Create a copy of ReportForm
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ReportFormCopyWith<_ReportForm> get copyWith => __$ReportFormCopyWithImpl<_ReportForm>(this, _$identity);



@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ReportForm&&(identical(other.from, from) || other.from == from)&&(identical(other.to, to) || other.to == to)&&(identical(other.periodBy, periodBy) || other.periodBy == periodBy)&&const DeepCollectionEquality().equals(other.statuses, _statuses)&&const DeepCollectionEquality().equals(other.types, _types)&&const DeepCollectionEquality().equals(other.categories, _categories)&&const DeepCollectionEquality().equals(other.cis, _cis)&&(identical(other.assignee, assignee) || other.assignee == assignee)&&(identical(other.approvedBy, approvedBy) || other.approvedBy == approvedBy)&&(identical(other.q, q) || other.q == q)&&(identical(other.includeAuditTrail, includeAuditTrail) || other.includeAuditTrail == includeAuditTrail));
}


@override
int get hashCode {
    return Object.hash(runtimeType,from,to,periodBy,const DeepCollectionEquality().hash(_statuses),const DeepCollectionEquality().hash(_types),const DeepCollectionEquality().hash(_categories),const DeepCollectionEquality().hash(_cis),assignee,approvedBy,q,includeAuditTrail);
}

@override
String toString() {
    return 'ReportForm(from: $from, to: $to, periodBy: $periodBy, statuses: $statuses, types: $types, categories: $categories, cis: $cis, assignee: $assignee, approvedBy: $approvedBy, q: $q, includeAuditTrail: $includeAuditTrail)';
}


}

/// @nodoc
abstract mixin class _$ReportFormCopyWith<$Res> implements $ReportFormCopyWith<$Res> {
  factory _$ReportFormCopyWith(_ReportForm value, $Res Function(_ReportForm) _then) = __$ReportFormCopyWithImpl;
@override @useResult
$Res call({
 String? from, String? to, String periodBy, List<String> statuses, List<String> types, List<String> categories, List<String> cis, String? assignee, String? approvedBy, String q, bool includeAuditTrail
});




}
/// @nodoc
class __$ReportFormCopyWithImpl<$Res>
    implements _$ReportFormCopyWith<$Res> {
  __$ReportFormCopyWithImpl(this._self, this._then);

  final _ReportForm _self;
  final $Res Function(_ReportForm) _then;

/// Create a copy of ReportForm
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? from = freezed,Object? to = freezed,Object? periodBy = null,Object? statuses = null,Object? types = null,Object? categories = null,Object? cis = null,Object? assignee = freezed,Object? approvedBy = freezed,Object? q = null,Object? includeAuditTrail = null,}) {
  return _then(_ReportForm(
from: freezed == from ? _self.from : from // ignore: cast_nullable_to_non_nullable
as String?,to: freezed == to ? _self.to : to // ignore: cast_nullable_to_non_nullable
as String?,periodBy: null == periodBy ? _self.periodBy : periodBy // ignore: cast_nullable_to_non_nullable
as String,statuses: null == statuses ? _self._statuses : statuses // ignore: cast_nullable_to_non_nullable
as List<String>,types: null == types ? _self._types : types // ignore: cast_nullable_to_non_nullable
as List<String>,categories: null == categories ? _self._categories : categories // ignore: cast_nullable_to_non_nullable
as List<String>,cis: null == cis ? _self._cis : cis // ignore: cast_nullable_to_non_nullable
as List<String>,assignee: freezed == assignee ? _self.assignee : assignee // ignore: cast_nullable_to_non_nullable
as String?,approvedBy: freezed == approvedBy ? _self.approvedBy : approvedBy // ignore: cast_nullable_to_non_nullable
as String?,q: null == q ? _self.q : q // ignore: cast_nullable_to_non_nullable
as String,includeAuditTrail: null == includeAuditTrail ? _self.includeAuditTrail : includeAuditTrail // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}

// dart format on
