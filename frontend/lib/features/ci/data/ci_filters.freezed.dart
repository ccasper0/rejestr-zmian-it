// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'ci_filters.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$CiFilters {

 String get q; List<String> get types; bool? get active; int get page;
/// Create a copy of CiFilters
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CiFiltersCopyWith<CiFilters> get copyWith => _$CiFiltersCopyWithImpl<CiFilters>(this as CiFilters, _$identity);



@override
bool operator ==(Object other) {
  final _this = this as CiFilters;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CiFilters&&(identical(other.q, _this.q) || other.q == _this.q)&&const DeepCollectionEquality().equals(other.types, _this.types)&&(identical(other.active, _this.active) || other.active == _this.active)&&(identical(other.page, _this.page) || other.page == _this.page));
}


@override
int get hashCode {
  final _this = this as CiFilters;
  return Object.hash(runtimeType,_this.q,const DeepCollectionEquality().hash(_this.types),_this.active,_this.page);
}

@override
String toString() {
  final _this = this as CiFilters;
  return 'CiFilters(q: ${_this.q}, types: ${_this.types}, active: ${_this.active}, page: ${_this.page})';
}


}

/// @nodoc
abstract mixin class $CiFiltersCopyWith<$Res>  {
  factory $CiFiltersCopyWith(CiFilters value, $Res Function(CiFilters) _then) = _$CiFiltersCopyWithImpl;
@useResult
$Res call({
 String q, List<String> types, bool? active, int page
});




}
/// @nodoc
class _$CiFiltersCopyWithImpl<$Res>
    implements $CiFiltersCopyWith<$Res> {
  _$CiFiltersCopyWithImpl(this._self, this._then);

  final CiFilters _self;
  final $Res Function(CiFilters) _then;

/// Create a copy of CiFilters
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? q = null,Object? types = null,Object? active = freezed,Object? page = null,}) {
  return _then(CiFilters(
q: null == q ? _self.q : q // ignore: cast_nullable_to_non_nullable
as String,types: null == types ? _self.types : types // ignore: cast_nullable_to_non_nullable
as List<String>,active: freezed == active ? _self.active : active // ignore: cast_nullable_to_non_nullable
as bool?,page: null == page ? _self.page : page // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

}


/// Adds pattern-matching-related methods to [CiFilters].
extension CiFiltersPatterns on CiFilters {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CiFilters value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CiFilters() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CiFilters value)  $default,){
final _that = this;
switch (_that) {
case _CiFilters():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CiFilters value)?  $default,){
final _that = this;
switch (_that) {
case _CiFilters() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String q,  List<String> types,  bool? active,  int page)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CiFilters() when $default != null:
return $default(_that.q,_that.types,_that.active,_that.page);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String q,  List<String> types,  bool? active,  int page)  $default,) {final _that = this;
switch (_that) {
case _CiFilters():
return $default(_that.q,_that.types,_that.active,_that.page);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String q,  List<String> types,  bool? active,  int page)?  $default,) {final _that = this;
switch (_that) {
case _CiFilters() when $default != null:
return $default(_that.q,_that.types,_that.active,_that.page);case _:
  return null;

}
}

}

/// @nodoc


class _CiFilters extends CiFilters {
  const _CiFilters({this.q = '',  List<String> types = const <String>[], this.active, this.page = 1}): _types = types,super._();
  

@override@JsonKey() final  String q;
 final  List<String> _types;
@override@JsonKey() List<String> get types {
  if (_types is EqualUnmodifiableListView) return _types;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_types);
}

@override final  bool? active;
@override@JsonKey() final  int page;

/// Create a copy of CiFilters
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CiFiltersCopyWith<_CiFilters> get copyWith => __$CiFiltersCopyWithImpl<_CiFilters>(this, _$identity);



@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _CiFilters&&(identical(other.q, q) || other.q == q)&&const DeepCollectionEquality().equals(other.types, _types)&&(identical(other.active, active) || other.active == active)&&(identical(other.page, page) || other.page == page));
}


@override
int get hashCode {
    return Object.hash(runtimeType,q,const DeepCollectionEquality().hash(_types),active,page);
}

@override
String toString() {
    return 'CiFilters(q: $q, types: $types, active: $active, page: $page)';
}


}

/// @nodoc
abstract mixin class _$CiFiltersCopyWith<$Res> implements $CiFiltersCopyWith<$Res> {
  factory _$CiFiltersCopyWith(_CiFilters value, $Res Function(_CiFilters) _then) = __$CiFiltersCopyWithImpl;
@override @useResult
$Res call({
 String q, List<String> types, bool? active, int page
});




}
/// @nodoc
class __$CiFiltersCopyWithImpl<$Res>
    implements _$CiFiltersCopyWith<$Res> {
  __$CiFiltersCopyWithImpl(this._self, this._then);

  final _CiFilters _self;
  final $Res Function(_CiFilters) _then;

/// Create a copy of CiFilters
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? q = null,Object? types = null,Object? active = freezed,Object? page = null,}) {
  return _then(_CiFilters(
q: null == q ? _self.q : q // ignore: cast_nullable_to_non_nullable
as String,types: null == types ? _self._types : types // ignore: cast_nullable_to_non_nullable
as List<String>,active: freezed == active ? _self.active : active // ignore: cast_nullable_to_non_nullable
as bool?,page: null == page ? _self.page : page // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}

// dart format on
