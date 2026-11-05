// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'auth.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$DevUser {

 String get externalId; String get displayName; String get email; bool get isAppAdmin; bool get isActive;
/// Create a copy of DevUser
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DevUserCopyWith<DevUser> get copyWith => _$DevUserCopyWithImpl<DevUser>(this as DevUser, _$identity);

  /// Serializes this DevUser to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as DevUser;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DevUser&&(identical(other.externalId, _this.externalId) || other.externalId == _this.externalId)&&(identical(other.displayName, _this.displayName) || other.displayName == _this.displayName)&&(identical(other.email, _this.email) || other.email == _this.email)&&(identical(other.isAppAdmin, _this.isAppAdmin) || other.isAppAdmin == _this.isAppAdmin)&&(identical(other.isActive, _this.isActive) || other.isActive == _this.isActive));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as DevUser;
  return Object.hash(runtimeType,_this.externalId,_this.displayName,_this.email,_this.isAppAdmin,_this.isActive);
}

@override
String toString() {
  final _this = this as DevUser;
  return 'DevUser(externalId: ${_this.externalId}, displayName: ${_this.displayName}, email: ${_this.email}, isAppAdmin: ${_this.isAppAdmin}, isActive: ${_this.isActive})';
}


}

/// @nodoc
abstract mixin class $DevUserCopyWith<$Res>  {
  factory $DevUserCopyWith(DevUser value, $Res Function(DevUser) _then) = _$DevUserCopyWithImpl;
@useResult
$Res call({
 String externalId, String displayName, String email, bool isAppAdmin, bool isActive
});




}
/// @nodoc
class _$DevUserCopyWithImpl<$Res>
    implements $DevUserCopyWith<$Res> {
  _$DevUserCopyWithImpl(this._self, this._then);

  final DevUser _self;
  final $Res Function(DevUser) _then;

/// Create a copy of DevUser
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? externalId = null,Object? displayName = null,Object? email = null,Object? isAppAdmin = null,Object? isActive = null,}) {
  return _then(DevUser(
externalId: null == externalId ? _self.externalId : externalId // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,email: null == email ? _self.email : email // ignore: cast_nullable_to_non_nullable
as String,isAppAdmin: null == isAppAdmin ? _self.isAppAdmin : isAppAdmin // ignore: cast_nullable_to_non_nullable
as bool,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [DevUser].
extension DevUserPatterns on DevUser {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DevUser value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DevUser() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DevUser value)  $default,){
final _that = this;
switch (_that) {
case _DevUser():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DevUser value)?  $default,){
final _that = this;
switch (_that) {
case _DevUser() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String externalId,  String displayName,  String email,  bool isAppAdmin,  bool isActive)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DevUser() when $default != null:
return $default(_that.externalId,_that.displayName,_that.email,_that.isAppAdmin,_that.isActive);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String externalId,  String displayName,  String email,  bool isAppAdmin,  bool isActive)  $default,) {final _that = this;
switch (_that) {
case _DevUser():
return $default(_that.externalId,_that.displayName,_that.email,_that.isAppAdmin,_that.isActive);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String externalId,  String displayName,  String email,  bool isAppAdmin,  bool isActive)?  $default,) {final _that = this;
switch (_that) {
case _DevUser() when $default != null:
return $default(_that.externalId,_that.displayName,_that.email,_that.isAppAdmin,_that.isActive);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _DevUser implements DevUser {
  const _DevUser({required this.externalId, required this.displayName, this.email = '', this.isAppAdmin = false, this.isActive = true});
  factory _DevUser.fromJson(Map<String, dynamic> json) => _$DevUserFromJson(json);

@override final  String externalId;
@override final  String displayName;
@override@JsonKey() final  String email;
@override@JsonKey() final  bool isAppAdmin;
@override@JsonKey() final  bool isActive;

/// Create a copy of DevUser
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DevUserCopyWith<_DevUser> get copyWith => __$DevUserCopyWithImpl<_DevUser>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DevUserToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _DevUser&&(identical(other.externalId, externalId) || other.externalId == externalId)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.email, email) || other.email == email)&&(identical(other.isAppAdmin, isAppAdmin) || other.isAppAdmin == isAppAdmin)&&(identical(other.isActive, isActive) || other.isActive == isActive));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,externalId,displayName,email,isAppAdmin,isActive);
}

@override
String toString() {
    return 'DevUser(externalId: $externalId, displayName: $displayName, email: $email, isAppAdmin: $isAppAdmin, isActive: $isActive)';
}


}

/// @nodoc
abstract mixin class _$DevUserCopyWith<$Res> implements $DevUserCopyWith<$Res> {
  factory _$DevUserCopyWith(_DevUser value, $Res Function(_DevUser) _then) = __$DevUserCopyWithImpl;
@override @useResult
$Res call({
 String externalId, String displayName, String email, bool isAppAdmin, bool isActive
});




}
/// @nodoc
class __$DevUserCopyWithImpl<$Res>
    implements _$DevUserCopyWith<$Res> {
  __$DevUserCopyWithImpl(this._self, this._then);

  final _DevUser _self;
  final $Res Function(_DevUser) _then;

/// Create a copy of DevUser
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? externalId = null,Object? displayName = null,Object? email = null,Object? isAppAdmin = null,Object? isActive = null,}) {
  return _then(_DevUser(
externalId: null == externalId ? _self.externalId : externalId // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,email: null == email ? _self.email : email // ignore: cast_nullable_to_non_nullable
as String,isAppAdmin: null == isAppAdmin ? _self.isAppAdmin : isAppAdmin // ignore: cast_nullable_to_non_nullable
as bool,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}

// dart format on
