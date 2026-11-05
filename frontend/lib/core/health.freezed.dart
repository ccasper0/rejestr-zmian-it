// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'health.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$HealthInfo {

 String get status; String? get version;
/// Create a copy of HealthInfo
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$HealthInfoCopyWith<HealthInfo> get copyWith => _$HealthInfoCopyWithImpl<HealthInfo>(this as HealthInfo, _$identity);

  /// Serializes this HealthInfo to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as HealthInfo;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is HealthInfo&&(identical(other.status, _this.status) || other.status == _this.status)&&(identical(other.version, _this.version) || other.version == _this.version));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as HealthInfo;
  return Object.hash(runtimeType,_this.status,_this.version);
}

@override
String toString() {
  final _this = this as HealthInfo;
  return 'HealthInfo(status: ${_this.status}, version: ${_this.version})';
}


}

/// @nodoc
abstract mixin class $HealthInfoCopyWith<$Res>  {
  factory $HealthInfoCopyWith(HealthInfo value, $Res Function(HealthInfo) _then) = _$HealthInfoCopyWithImpl;
@useResult
$Res call({
 String status, String? version
});




}
/// @nodoc
class _$HealthInfoCopyWithImpl<$Res>
    implements $HealthInfoCopyWith<$Res> {
  _$HealthInfoCopyWithImpl(this._self, this._then);

  final HealthInfo _self;
  final $Res Function(HealthInfo) _then;

/// Create a copy of HealthInfo
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? status = null,Object? version = freezed,}) {
  return _then(HealthInfo(
status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,version: freezed == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [HealthInfo].
extension HealthInfoPatterns on HealthInfo {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _HealthInfo value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _HealthInfo() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _HealthInfo value)  $default,){
final _that = this;
switch (_that) {
case _HealthInfo():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _HealthInfo value)?  $default,){
final _that = this;
switch (_that) {
case _HealthInfo() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String status,  String? version)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _HealthInfo() when $default != null:
return $default(_that.status,_that.version);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String status,  String? version)  $default,) {final _that = this;
switch (_that) {
case _HealthInfo():
return $default(_that.status,_that.version);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String status,  String? version)?  $default,) {final _that = this;
switch (_that) {
case _HealthInfo() when $default != null:
return $default(_that.status,_that.version);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _HealthInfo implements HealthInfo {
  const _HealthInfo({this.status = 'ok', this.version});
  factory _HealthInfo.fromJson(Map<String, dynamic> json) => _$HealthInfoFromJson(json);

@override@JsonKey() final  String status;
@override final  String? version;

/// Create a copy of HealthInfo
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$HealthInfoCopyWith<_HealthInfo> get copyWith => __$HealthInfoCopyWithImpl<_HealthInfo>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$HealthInfoToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _HealthInfo&&(identical(other.status, status) || other.status == status)&&(identical(other.version, version) || other.version == version));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,status,version);
}

@override
String toString() {
    return 'HealthInfo(status: $status, version: $version)';
}


}

/// @nodoc
abstract mixin class _$HealthInfoCopyWith<$Res> implements $HealthInfoCopyWith<$Res> {
  factory _$HealthInfoCopyWith(_HealthInfo value, $Res Function(_HealthInfo) _then) = __$HealthInfoCopyWithImpl;
@override @useResult
$Res call({
 String status, String? version
});




}
/// @nodoc
class __$HealthInfoCopyWithImpl<$Res>
    implements _$HealthInfoCopyWith<$Res> {
  __$HealthInfoCopyWithImpl(this._self, this._then);

  final _HealthInfo _self;
  final $Res Function(_HealthInfo) _then;

/// Create a copy of HealthInfo
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? status = null,Object? version = freezed,}) {
  return _then(_HealthInfo(
status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,version: freezed == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}

// dart format on
