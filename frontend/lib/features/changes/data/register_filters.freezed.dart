// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'register_filters.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$RegisterFilters {

 String get q; List<String> get statuses; List<String> get types; List<String> get categories; List<String> get cis; String? get assignee; String? get approvedBy; String? get from; String? get to; String get periodBy; String get sort; int get page;
/// Create a copy of RegisterFilters
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$RegisterFiltersCopyWith<RegisterFilters> get copyWith => _$RegisterFiltersCopyWithImpl<RegisterFilters>(this as RegisterFilters, _$identity);



@override
bool operator ==(Object other) {
  final _this = this as RegisterFilters;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is RegisterFilters&&(identical(other.q, _this.q) || other.q == _this.q)&&const DeepCollectionEquality().equals(other.statuses, _this.statuses)&&const DeepCollectionEquality().equals(other.types, _this.types)&&const DeepCollectionEquality().equals(other.categories, _this.categories)&&const DeepCollectionEquality().equals(other.cis, _this.cis)&&(identical(other.assignee, _this.assignee) || other.assignee == _this.assignee)&&(identical(other.approvedBy, _this.approvedBy) || other.approvedBy == _this.approvedBy)&&(identical(other.from, _this.from) || other.from == _this.from)&&(identical(other.to, _this.to) || other.to == _this.to)&&(identical(other.periodBy, _this.periodBy) || other.periodBy == _this.periodBy)&&(identical(other.sort, _this.sort) || other.sort == _this.sort)&&(identical(other.page, _this.page) || other.page == _this.page));
}


@override
int get hashCode {
  final _this = this as RegisterFilters;
  return Object.hash(runtimeType,_this.q,const DeepCollectionEquality().hash(_this.statuses),const DeepCollectionEquality().hash(_this.types),const DeepCollectionEquality().hash(_this.categories),const DeepCollectionEquality().hash(_this.cis),_this.assignee,_this.approvedBy,_this.from,_this.to,_this.periodBy,_this.sort,_this.page);
}

@override
String toString() {
  final _this = this as RegisterFilters;
  return 'RegisterFilters(q: ${_this.q}, statuses: ${_this.statuses}, types: ${_this.types}, categories: ${_this.categories}, cis: ${_this.cis}, assignee: ${_this.assignee}, approvedBy: ${_this.approvedBy}, from: ${_this.from}, to: ${_this.to}, periodBy: ${_this.periodBy}, sort: ${_this.sort}, page: ${_this.page})';
}


}

/// @nodoc
abstract mixin class $RegisterFiltersCopyWith<$Res>  {
  factory $RegisterFiltersCopyWith(RegisterFilters value, $Res Function(RegisterFilters) _then) = _$RegisterFiltersCopyWithImpl;
@useResult
$Res call({
 String q, List<String> statuses, List<String> types, List<String> categories, List<String> cis, String? assignee, String? approvedBy, String? from, String? to, String periodBy, String sort, int page
});




}
/// @nodoc
class _$RegisterFiltersCopyWithImpl<$Res>
    implements $RegisterFiltersCopyWith<$Res> {
  _$RegisterFiltersCopyWithImpl(this._self, this._then);

  final RegisterFilters _self;
  final $Res Function(RegisterFilters) _then;

/// Create a copy of RegisterFilters
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? q = null,Object? statuses = null,Object? types = null,Object? categories = null,Object? cis = null,Object? assignee = freezed,Object? approvedBy = freezed,Object? from = freezed,Object? to = freezed,Object? periodBy = null,Object? sort = null,Object? page = null,}) {
  return _then(RegisterFilters(
q: null == q ? _self.q : q // ignore: cast_nullable_to_non_nullable
as String,statuses: null == statuses ? _self.statuses : statuses // ignore: cast_nullable_to_non_nullable
as List<String>,types: null == types ? _self.types : types // ignore: cast_nullable_to_non_nullable
as List<String>,categories: null == categories ? _self.categories : categories // ignore: cast_nullable_to_non_nullable
as List<String>,cis: null == cis ? _self.cis : cis // ignore: cast_nullable_to_non_nullable
as List<String>,assignee: freezed == assignee ? _self.assignee : assignee // ignore: cast_nullable_to_non_nullable
as String?,approvedBy: freezed == approvedBy ? _self.approvedBy : approvedBy // ignore: cast_nullable_to_non_nullable
as String?,from: freezed == from ? _self.from : from // ignore: cast_nullable_to_non_nullable
as String?,to: freezed == to ? _self.to : to // ignore: cast_nullable_to_non_nullable
as String?,periodBy: null == periodBy ? _self.periodBy : periodBy // ignore: cast_nullable_to_non_nullable
as String,sort: null == sort ? _self.sort : sort // ignore: cast_nullable_to_non_nullable
as String,page: null == page ? _self.page : page // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

}


/// Adds pattern-matching-related methods to [RegisterFilters].
extension RegisterFiltersPatterns on RegisterFilters {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _RegisterFilters value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _RegisterFilters() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _RegisterFilters value)  $default,){
final _that = this;
switch (_that) {
case _RegisterFilters():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _RegisterFilters value)?  $default,){
final _that = this;
switch (_that) {
case _RegisterFilters() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String q,  List<String> statuses,  List<String> types,  List<String> categories,  List<String> cis,  String? assignee,  String? approvedBy,  String? from,  String? to,  String periodBy,  String sort,  int page)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _RegisterFilters() when $default != null:
return $default(_that.q,_that.statuses,_that.types,_that.categories,_that.cis,_that.assignee,_that.approvedBy,_that.from,_that.to,_that.periodBy,_that.sort,_that.page);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String q,  List<String> statuses,  List<String> types,  List<String> categories,  List<String> cis,  String? assignee,  String? approvedBy,  String? from,  String? to,  String periodBy,  String sort,  int page)  $default,) {final _that = this;
switch (_that) {
case _RegisterFilters():
return $default(_that.q,_that.statuses,_that.types,_that.categories,_that.cis,_that.assignee,_that.approvedBy,_that.from,_that.to,_that.periodBy,_that.sort,_that.page);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String q,  List<String> statuses,  List<String> types,  List<String> categories,  List<String> cis,  String? assignee,  String? approvedBy,  String? from,  String? to,  String periodBy,  String sort,  int page)?  $default,) {final _that = this;
switch (_that) {
case _RegisterFilters() when $default != null:
return $default(_that.q,_that.statuses,_that.types,_that.categories,_that.cis,_that.assignee,_that.approvedBy,_that.from,_that.to,_that.periodBy,_that.sort,_that.page);case _:
  return null;

}
}

}

/// @nodoc


class _RegisterFilters extends RegisterFilters {
  const _RegisterFilters({this.q = '',  List<String> statuses = const <String>[],  List<String> types = const <String>[],  List<String> categories = const <String>[],  List<String> cis = const <String>[], this.assignee, this.approvedBy, this.from, this.to, this.periodBy = RegisterFilters.defaultPeriodBy, this.sort = RegisterFilters.defaultSort, this.page = 1}): _statuses = statuses,_types = types,_categories = categories,_cis = cis,super._();
  

@override@JsonKey() final  String q;
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
@override final  String? from;
@override final  String? to;
@override@JsonKey() final  String periodBy;
@override@JsonKey() final  String sort;
@override@JsonKey() final  int page;

/// Create a copy of RegisterFilters
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$RegisterFiltersCopyWith<_RegisterFilters> get copyWith => __$RegisterFiltersCopyWithImpl<_RegisterFilters>(this, _$identity);



@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _RegisterFilters&&(identical(other.q, q) || other.q == q)&&const DeepCollectionEquality().equals(other.statuses, _statuses)&&const DeepCollectionEquality().equals(other.types, _types)&&const DeepCollectionEquality().equals(other.categories, _categories)&&const DeepCollectionEquality().equals(other.cis, _cis)&&(identical(other.assignee, assignee) || other.assignee == assignee)&&(identical(other.approvedBy, approvedBy) || other.approvedBy == approvedBy)&&(identical(other.from, from) || other.from == from)&&(identical(other.to, to) || other.to == to)&&(identical(other.periodBy, periodBy) || other.periodBy == periodBy)&&(identical(other.sort, sort) || other.sort == sort)&&(identical(other.page, page) || other.page == page));
}


@override
int get hashCode {
    return Object.hash(runtimeType,q,const DeepCollectionEquality().hash(_statuses),const DeepCollectionEquality().hash(_types),const DeepCollectionEquality().hash(_categories),const DeepCollectionEquality().hash(_cis),assignee,approvedBy,from,to,periodBy,sort,page);
}

@override
String toString() {
    return 'RegisterFilters(q: $q, statuses: $statuses, types: $types, categories: $categories, cis: $cis, assignee: $assignee, approvedBy: $approvedBy, from: $from, to: $to, periodBy: $periodBy, sort: $sort, page: $page)';
}


}

/// @nodoc
abstract mixin class _$RegisterFiltersCopyWith<$Res> implements $RegisterFiltersCopyWith<$Res> {
  factory _$RegisterFiltersCopyWith(_RegisterFilters value, $Res Function(_RegisterFilters) _then) = __$RegisterFiltersCopyWithImpl;
@override @useResult
$Res call({
 String q, List<String> statuses, List<String> types, List<String> categories, List<String> cis, String? assignee, String? approvedBy, String? from, String? to, String periodBy, String sort, int page
});




}
/// @nodoc
class __$RegisterFiltersCopyWithImpl<$Res>
    implements _$RegisterFiltersCopyWith<$Res> {
  __$RegisterFiltersCopyWithImpl(this._self, this._then);

  final _RegisterFilters _self;
  final $Res Function(_RegisterFilters) _then;

/// Create a copy of RegisterFilters
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? q = null,Object? statuses = null,Object? types = null,Object? categories = null,Object? cis = null,Object? assignee = freezed,Object? approvedBy = freezed,Object? from = freezed,Object? to = freezed,Object? periodBy = null,Object? sort = null,Object? page = null,}) {
  return _then(_RegisterFilters(
q: null == q ? _self.q : q // ignore: cast_nullable_to_non_nullable
as String,statuses: null == statuses ? _self._statuses : statuses // ignore: cast_nullable_to_non_nullable
as List<String>,types: null == types ? _self._types : types // ignore: cast_nullable_to_non_nullable
as List<String>,categories: null == categories ? _self._categories : categories // ignore: cast_nullable_to_non_nullable
as List<String>,cis: null == cis ? _self._cis : cis // ignore: cast_nullable_to_non_nullable
as List<String>,assignee: freezed == assignee ? _self.assignee : assignee // ignore: cast_nullable_to_non_nullable
as String?,approvedBy: freezed == approvedBy ? _self.approvedBy : approvedBy // ignore: cast_nullable_to_non_nullable
as String?,from: freezed == from ? _self.from : from // ignore: cast_nullable_to_non_nullable
as String?,to: freezed == to ? _self.to : to // ignore: cast_nullable_to_non_nullable
as String?,periodBy: null == periodBy ? _self.periodBy : periodBy // ignore: cast_nullable_to_non_nullable
as String,sort: null == sort ? _self.sort : sort // ignore: cast_nullable_to_non_nullable
as String,page: null == page ? _self.page : page // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}

// dart format on
