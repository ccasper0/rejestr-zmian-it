// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'audit_filters.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$AuditFilters {

 String? get entityType; String? get action; String? get actor; String? get from; String? get to; int get page;
/// Create a copy of AuditFilters
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AuditFiltersCopyWith<AuditFilters> get copyWith => _$AuditFiltersCopyWithImpl<AuditFilters>(this as AuditFilters, _$identity);



@override
bool operator ==(Object other) {
  final _this = this as AuditFilters;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AuditFilters&&(identical(other.entityType, _this.entityType) || other.entityType == _this.entityType)&&(identical(other.action, _this.action) || other.action == _this.action)&&(identical(other.actor, _this.actor) || other.actor == _this.actor)&&(identical(other.from, _this.from) || other.from == _this.from)&&(identical(other.to, _this.to) || other.to == _this.to)&&(identical(other.page, _this.page) || other.page == _this.page));
}


@override
int get hashCode {
  final _this = this as AuditFilters;
  return Object.hash(runtimeType,_this.entityType,_this.action,_this.actor,_this.from,_this.to,_this.page);
}

@override
String toString() {
  final _this = this as AuditFilters;
  return 'AuditFilters(entityType: ${_this.entityType}, action: ${_this.action}, actor: ${_this.actor}, from: ${_this.from}, to: ${_this.to}, page: ${_this.page})';
}


}

/// @nodoc
abstract mixin class $AuditFiltersCopyWith<$Res>  {
  factory $AuditFiltersCopyWith(AuditFilters value, $Res Function(AuditFilters) _then) = _$AuditFiltersCopyWithImpl;
@useResult
$Res call({
 String? entityType, String? action, String? actor, String? from, String? to, int page
});




}
/// @nodoc
class _$AuditFiltersCopyWithImpl<$Res>
    implements $AuditFiltersCopyWith<$Res> {
  _$AuditFiltersCopyWithImpl(this._self, this._then);

  final AuditFilters _self;
  final $Res Function(AuditFilters) _then;

/// Create a copy of AuditFilters
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? entityType = freezed,Object? action = freezed,Object? actor = freezed,Object? from = freezed,Object? to = freezed,Object? page = null,}) {
  return _then(AuditFilters(
entityType: freezed == entityType ? _self.entityType : entityType // ignore: cast_nullable_to_non_nullable
as String?,action: freezed == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String?,actor: freezed == actor ? _self.actor : actor // ignore: cast_nullable_to_non_nullable
as String?,from: freezed == from ? _self.from : from // ignore: cast_nullable_to_non_nullable
as String?,to: freezed == to ? _self.to : to // ignore: cast_nullable_to_non_nullable
as String?,page: null == page ? _self.page : page // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

}


/// Adds pattern-matching-related methods to [AuditFilters].
extension AuditFiltersPatterns on AuditFilters {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AuditFilters value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AuditFilters() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AuditFilters value)  $default,){
final _that = this;
switch (_that) {
case _AuditFilters():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AuditFilters value)?  $default,){
final _that = this;
switch (_that) {
case _AuditFilters() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String? entityType,  String? action,  String? actor,  String? from,  String? to,  int page)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AuditFilters() when $default != null:
return $default(_that.entityType,_that.action,_that.actor,_that.from,_that.to,_that.page);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String? entityType,  String? action,  String? actor,  String? from,  String? to,  int page)  $default,) {final _that = this;
switch (_that) {
case _AuditFilters():
return $default(_that.entityType,_that.action,_that.actor,_that.from,_that.to,_that.page);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String? entityType,  String? action,  String? actor,  String? from,  String? to,  int page)?  $default,) {final _that = this;
switch (_that) {
case _AuditFilters() when $default != null:
return $default(_that.entityType,_that.action,_that.actor,_that.from,_that.to,_that.page);case _:
  return null;

}
}

}

/// @nodoc


class _AuditFilters extends AuditFilters {
  const _AuditFilters({this.entityType, this.action, this.actor, this.from, this.to, this.page = 1}): super._();
  

@override final  String? entityType;
@override final  String? action;
@override final  String? actor;
@override final  String? from;
@override final  String? to;
@override@JsonKey() final  int page;

/// Create a copy of AuditFilters
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AuditFiltersCopyWith<_AuditFilters> get copyWith => __$AuditFiltersCopyWithImpl<_AuditFilters>(this, _$identity);



@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _AuditFilters&&(identical(other.entityType, entityType) || other.entityType == entityType)&&(identical(other.action, action) || other.action == action)&&(identical(other.actor, actor) || other.actor == actor)&&(identical(other.from, from) || other.from == from)&&(identical(other.to, to) || other.to == to)&&(identical(other.page, page) || other.page == page));
}


@override
int get hashCode {
    return Object.hash(runtimeType,entityType,action,actor,from,to,page);
}

@override
String toString() {
    return 'AuditFilters(entityType: $entityType, action: $action, actor: $actor, from: $from, to: $to, page: $page)';
}


}

/// @nodoc
abstract mixin class _$AuditFiltersCopyWith<$Res> implements $AuditFiltersCopyWith<$Res> {
  factory _$AuditFiltersCopyWith(_AuditFilters value, $Res Function(_AuditFilters) _then) = __$AuditFiltersCopyWithImpl;
@override @useResult
$Res call({
 String? entityType, String? action, String? actor, String? from, String? to, int page
});




}
/// @nodoc
class __$AuditFiltersCopyWithImpl<$Res>
    implements _$AuditFiltersCopyWith<$Res> {
  __$AuditFiltersCopyWithImpl(this._self, this._then);

  final _AuditFilters _self;
  final $Res Function(_AuditFilters) _then;

/// Create a copy of AuditFilters
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? entityType = freezed,Object? action = freezed,Object? actor = freezed,Object? from = freezed,Object? to = freezed,Object? page = null,}) {
  return _then(_AuditFilters(
entityType: freezed == entityType ? _self.entityType : entityType // ignore: cast_nullable_to_non_nullable
as String?,action: freezed == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String?,actor: freezed == actor ? _self.actor : actor // ignore: cast_nullable_to_non_nullable
as String?,from: freezed == from ? _self.from : from // ignore: cast_nullable_to_non_nullable
as String?,to: freezed == to ? _self.to : to // ignore: cast_nullable_to_non_nullable
as String?,page: null == page ? _self.page : page // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}

// dart format on
