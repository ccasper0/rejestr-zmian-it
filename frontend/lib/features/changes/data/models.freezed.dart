// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'models.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$UserRef {

 String get id; String get displayName;
/// Create a copy of UserRef
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$UserRefCopyWith<UserRef> get copyWith => _$UserRefCopyWithImpl<UserRef>(this as UserRef, _$identity);

  /// Serializes this UserRef to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as UserRef;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is UserRef&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.displayName, _this.displayName) || other.displayName == _this.displayName));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as UserRef;
  return Object.hash(runtimeType,_this.id,_this.displayName);
}

@override
String toString() {
  final _this = this as UserRef;
  return 'UserRef(id: ${_this.id}, displayName: ${_this.displayName})';
}


}

/// @nodoc
abstract mixin class $UserRefCopyWith<$Res>  {
  factory $UserRefCopyWith(UserRef value, $Res Function(UserRef) _then) = _$UserRefCopyWithImpl;
@useResult
$Res call({
 String id, String displayName
});




}
/// @nodoc
class _$UserRefCopyWithImpl<$Res>
    implements $UserRefCopyWith<$Res> {
  _$UserRefCopyWithImpl(this._self, this._then);

  final UserRef _self;
  final $Res Function(UserRef) _then;

/// Create a copy of UserRef
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? displayName = null,}) {
  return _then(UserRef(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

}


/// Adds pattern-matching-related methods to [UserRef].
extension UserRefPatterns on UserRef {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _UserRef value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _UserRef() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _UserRef value)  $default,){
final _that = this;
switch (_that) {
case _UserRef():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _UserRef value)?  $default,){
final _that = this;
switch (_that) {
case _UserRef() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String displayName)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _UserRef() when $default != null:
return $default(_that.id,_that.displayName);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String displayName)  $default,) {final _that = this;
switch (_that) {
case _UserRef():
return $default(_that.id,_that.displayName);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String displayName)?  $default,) {final _that = this;
switch (_that) {
case _UserRef() when $default != null:
return $default(_that.id,_that.displayName);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _UserRef implements UserRef {
  const _UserRef({required this.id, required this.displayName});
  factory _UserRef.fromJson(Map<String, dynamic> json) => _$UserRefFromJson(json);

@override final  String id;
@override final  String displayName;

/// Create a copy of UserRef
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$UserRefCopyWith<_UserRef> get copyWith => __$UserRefCopyWithImpl<_UserRef>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$UserRefToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _UserRef&&(identical(other.id, id) || other.id == id)&&(identical(other.displayName, displayName) || other.displayName == displayName));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,displayName);
}

@override
String toString() {
    return 'UserRef(id: $id, displayName: $displayName)';
}


}

/// @nodoc
abstract mixin class _$UserRefCopyWith<$Res> implements $UserRefCopyWith<$Res> {
  factory _$UserRefCopyWith(_UserRef value, $Res Function(_UserRef) _then) = __$UserRefCopyWithImpl;
@override @useResult
$Res call({
 String id, String displayName
});




}
/// @nodoc
class __$UserRefCopyWithImpl<$Res>
    implements _$UserRefCopyWith<$Res> {
  __$UserRefCopyWithImpl(this._self, this._then);

  final _UserRef _self;
  final $Res Function(_UserRef) _then;

/// Create a copy of UserRef
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? displayName = null,}) {
  return _then(_UserRef(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,
  ));
}


}


/// @nodoc
mixin _$CategoryRef {

 String get id; String get code; String get name;
/// Create a copy of CategoryRef
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CategoryRefCopyWith<CategoryRef> get copyWith => _$CategoryRefCopyWithImpl<CategoryRef>(this as CategoryRef, _$identity);

  /// Serializes this CategoryRef to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as CategoryRef;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CategoryRef&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.code, _this.code) || other.code == _this.code)&&(identical(other.name, _this.name) || other.name == _this.name));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as CategoryRef;
  return Object.hash(runtimeType,_this.id,_this.code,_this.name);
}

@override
String toString() {
  final _this = this as CategoryRef;
  return 'CategoryRef(id: ${_this.id}, code: ${_this.code}, name: ${_this.name})';
}


}

/// @nodoc
abstract mixin class $CategoryRefCopyWith<$Res>  {
  factory $CategoryRefCopyWith(CategoryRef value, $Res Function(CategoryRef) _then) = _$CategoryRefCopyWithImpl;
@useResult
$Res call({
 String id, String code, String name
});




}
/// @nodoc
class _$CategoryRefCopyWithImpl<$Res>
    implements $CategoryRefCopyWith<$Res> {
  _$CategoryRefCopyWithImpl(this._self, this._then);

  final CategoryRef _self;
  final $Res Function(CategoryRef) _then;

/// Create a copy of CategoryRef
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? code = null,Object? name = null,}) {
  return _then(CategoryRef(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

}


/// Adds pattern-matching-related methods to [CategoryRef].
extension CategoryRefPatterns on CategoryRef {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CategoryRef value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CategoryRef() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CategoryRef value)  $default,){
final _that = this;
switch (_that) {
case _CategoryRef():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CategoryRef value)?  $default,){
final _that = this;
switch (_that) {
case _CategoryRef() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String code,  String name)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CategoryRef() when $default != null:
return $default(_that.id,_that.code,_that.name);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String code,  String name)  $default,) {final _that = this;
switch (_that) {
case _CategoryRef():
return $default(_that.id,_that.code,_that.name);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String code,  String name)?  $default,) {final _that = this;
switch (_that) {
case _CategoryRef() when $default != null:
return $default(_that.id,_that.code,_that.name);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _CategoryRef implements CategoryRef {
  const _CategoryRef({required this.id, required this.code, required this.name});
  factory _CategoryRef.fromJson(Map<String, dynamic> json) => _$CategoryRefFromJson(json);

@override final  String id;
@override final  String code;
@override final  String name;

/// Create a copy of CategoryRef
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CategoryRefCopyWith<_CategoryRef> get copyWith => __$CategoryRefCopyWithImpl<_CategoryRef>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$CategoryRefToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _CategoryRef&&(identical(other.id, id) || other.id == id)&&(identical(other.code, code) || other.code == code)&&(identical(other.name, name) || other.name == name));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,code,name);
}

@override
String toString() {
    return 'CategoryRef(id: $id, code: $code, name: $name)';
}


}

/// @nodoc
abstract mixin class _$CategoryRefCopyWith<$Res> implements $CategoryRefCopyWith<$Res> {
  factory _$CategoryRefCopyWith(_CategoryRef value, $Res Function(_CategoryRef) _then) = __$CategoryRefCopyWithImpl;
@override @useResult
$Res call({
 String id, String code, String name
});




}
/// @nodoc
class __$CategoryRefCopyWithImpl<$Res>
    implements _$CategoryRefCopyWith<$Res> {
  __$CategoryRefCopyWithImpl(this._self, this._then);

  final _CategoryRef _self;
  final $Res Function(_CategoryRef) _then;

/// Create a copy of CategoryRef
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? code = null,Object? name = null,}) {
  return _then(_CategoryRef(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,
  ));
}


}


/// @nodoc
mixin _$ChangeCi {

 String get id; String get identifier; String get name; String get ciTypeCode; bool get isActive; bool get snapshot; String? get currentIdentifier; String? get currentName; UserRef? get owner; bool get consented;
/// Create a copy of ChangeCi
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ChangeCiCopyWith<ChangeCi> get copyWith => _$ChangeCiCopyWithImpl<ChangeCi>(this as ChangeCi, _$identity);

  /// Serializes this ChangeCi to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ChangeCi;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ChangeCi&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.identifier, _this.identifier) || other.identifier == _this.identifier)&&(identical(other.name, _this.name) || other.name == _this.name)&&(identical(other.ciTypeCode, _this.ciTypeCode) || other.ciTypeCode == _this.ciTypeCode)&&(identical(other.isActive, _this.isActive) || other.isActive == _this.isActive)&&(identical(other.snapshot, _this.snapshot) || other.snapshot == _this.snapshot)&&(identical(other.currentIdentifier, _this.currentIdentifier) || other.currentIdentifier == _this.currentIdentifier)&&(identical(other.currentName, _this.currentName) || other.currentName == _this.currentName)&&(identical(other.owner, _this.owner) || other.owner == _this.owner)&&(identical(other.consented, _this.consented) || other.consented == _this.consented));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ChangeCi;
  return Object.hash(runtimeType,_this.id,_this.identifier,_this.name,_this.ciTypeCode,_this.isActive,_this.snapshot,_this.currentIdentifier,_this.currentName,_this.owner,_this.consented);
}

@override
String toString() {
  final _this = this as ChangeCi;
  return 'ChangeCi(id: ${_this.id}, identifier: ${_this.identifier}, name: ${_this.name}, ciTypeCode: ${_this.ciTypeCode}, isActive: ${_this.isActive}, snapshot: ${_this.snapshot}, currentIdentifier: ${_this.currentIdentifier}, currentName: ${_this.currentName}, owner: ${_this.owner}, consented: ${_this.consented})';
}


}

/// @nodoc
abstract mixin class $ChangeCiCopyWith<$Res>  {
  factory $ChangeCiCopyWith(ChangeCi value, $Res Function(ChangeCi) _then) = _$ChangeCiCopyWithImpl;
@useResult
$Res call({
 String id, String identifier, String name, String ciTypeCode, bool isActive, bool snapshot, String? currentIdentifier, String? currentName, UserRef? owner, bool consented
});


$UserRefCopyWith<$Res>? get owner;

}
/// @nodoc
class _$ChangeCiCopyWithImpl<$Res>
    implements $ChangeCiCopyWith<$Res> {
  _$ChangeCiCopyWithImpl(this._self, this._then);

  final ChangeCi _self;
  final $Res Function(ChangeCi) _then;

/// Create a copy of ChangeCi
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? identifier = null,Object? name = null,Object? ciTypeCode = null,Object? isActive = null,Object? snapshot = null,Object? currentIdentifier = freezed,Object? currentName = freezed,Object? owner = freezed,Object? consented = null,}) {
  return _then(ChangeCi(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,identifier: null == identifier ? _self.identifier : identifier // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,ciTypeCode: null == ciTypeCode ? _self.ciTypeCode : ciTypeCode // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,snapshot: null == snapshot ? _self.snapshot : snapshot // ignore: cast_nullable_to_non_nullable
as bool,currentIdentifier: freezed == currentIdentifier ? _self.currentIdentifier : currentIdentifier // ignore: cast_nullable_to_non_nullable
as String?,currentName: freezed == currentName ? _self.currentName : currentName // ignore: cast_nullable_to_non_nullable
as String?,owner: freezed == owner ? _self.owner : owner // ignore: cast_nullable_to_non_nullable
as UserRef?,consented: null == consented ? _self.consented : consented // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of ChangeCi
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get owner {
    if (_self.owner == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.owner!, (value) {
    return _then(_self.copyWith(owner: value));
  });
}
}


/// Adds pattern-matching-related methods to [ChangeCi].
extension ChangeCiPatterns on ChangeCi {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ChangeCi value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ChangeCi() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ChangeCi value)  $default,){
final _that = this;
switch (_that) {
case _ChangeCi():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ChangeCi value)?  $default,){
final _that = this;
switch (_that) {
case _ChangeCi() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String identifier,  String name,  String ciTypeCode,  bool isActive,  bool snapshot,  String? currentIdentifier,  String? currentName,  UserRef? owner,  bool consented)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ChangeCi() when $default != null:
return $default(_that.id,_that.identifier,_that.name,_that.ciTypeCode,_that.isActive,_that.snapshot,_that.currentIdentifier,_that.currentName,_that.owner,_that.consented);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String identifier,  String name,  String ciTypeCode,  bool isActive,  bool snapshot,  String? currentIdentifier,  String? currentName,  UserRef? owner,  bool consented)  $default,) {final _that = this;
switch (_that) {
case _ChangeCi():
return $default(_that.id,_that.identifier,_that.name,_that.ciTypeCode,_that.isActive,_that.snapshot,_that.currentIdentifier,_that.currentName,_that.owner,_that.consented);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String identifier,  String name,  String ciTypeCode,  bool isActive,  bool snapshot,  String? currentIdentifier,  String? currentName,  UserRef? owner,  bool consented)?  $default,) {final _that = this;
switch (_that) {
case _ChangeCi() when $default != null:
return $default(_that.id,_that.identifier,_that.name,_that.ciTypeCode,_that.isActive,_that.snapshot,_that.currentIdentifier,_that.currentName,_that.owner,_that.consented);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ChangeCi implements ChangeCi {
  const _ChangeCi({required this.id, required this.identifier, required this.name, this.ciTypeCode = '', this.isActive = true, this.snapshot = false, this.currentIdentifier, this.currentName, this.owner, this.consented = false});
  factory _ChangeCi.fromJson(Map<String, dynamic> json) => _$ChangeCiFromJson(json);

@override final  String id;
@override final  String identifier;
@override final  String name;
@override@JsonKey() final  String ciTypeCode;
@override@JsonKey() final  bool isActive;
@override@JsonKey() final  bool snapshot;
@override final  String? currentIdentifier;
@override final  String? currentName;
@override final  UserRef? owner;
@override@JsonKey() final  bool consented;

/// Create a copy of ChangeCi
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ChangeCiCopyWith<_ChangeCi> get copyWith => __$ChangeCiCopyWithImpl<_ChangeCi>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ChangeCiToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ChangeCi&&(identical(other.id, id) || other.id == id)&&(identical(other.identifier, identifier) || other.identifier == identifier)&&(identical(other.name, name) || other.name == name)&&(identical(other.ciTypeCode, ciTypeCode) || other.ciTypeCode == ciTypeCode)&&(identical(other.isActive, isActive) || other.isActive == isActive)&&(identical(other.snapshot, snapshot) || other.snapshot == snapshot)&&(identical(other.currentIdentifier, currentIdentifier) || other.currentIdentifier == currentIdentifier)&&(identical(other.currentName, currentName) || other.currentName == currentName)&&(identical(other.owner, owner) || other.owner == owner)&&(identical(other.consented, consented) || other.consented == consented));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,identifier,name,ciTypeCode,isActive,snapshot,currentIdentifier,currentName,owner,consented);
}

@override
String toString() {
    return 'ChangeCi(id: $id, identifier: $identifier, name: $name, ciTypeCode: $ciTypeCode, isActive: $isActive, snapshot: $snapshot, currentIdentifier: $currentIdentifier, currentName: $currentName, owner: $owner, consented: $consented)';
}


}

/// @nodoc
abstract mixin class _$ChangeCiCopyWith<$Res> implements $ChangeCiCopyWith<$Res> {
  factory _$ChangeCiCopyWith(_ChangeCi value, $Res Function(_ChangeCi) _then) = __$ChangeCiCopyWithImpl;
@override @useResult
$Res call({
 String id, String identifier, String name, String ciTypeCode, bool isActive, bool snapshot, String? currentIdentifier, String? currentName, UserRef? owner, bool consented
});


@override $UserRefCopyWith<$Res>? get owner;

}
/// @nodoc
class __$ChangeCiCopyWithImpl<$Res>
    implements _$ChangeCiCopyWith<$Res> {
  __$ChangeCiCopyWithImpl(this._self, this._then);

  final _ChangeCi _self;
  final $Res Function(_ChangeCi) _then;

/// Create a copy of ChangeCi
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? identifier = null,Object? name = null,Object? ciTypeCode = null,Object? isActive = null,Object? snapshot = null,Object? currentIdentifier = freezed,Object? currentName = freezed,Object? owner = freezed,Object? consented = null,}) {
  return _then(_ChangeCi(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,identifier: null == identifier ? _self.identifier : identifier // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,ciTypeCode: null == ciTypeCode ? _self.ciTypeCode : ciTypeCode // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,snapshot: null == snapshot ? _self.snapshot : snapshot // ignore: cast_nullable_to_non_nullable
as bool,currentIdentifier: freezed == currentIdentifier ? _self.currentIdentifier : currentIdentifier // ignore: cast_nullable_to_non_nullable
as String?,currentName: freezed == currentName ? _self.currentName : currentName // ignore: cast_nullable_to_non_nullable
as String?,owner: freezed == owner ? _self.owner : owner // ignore: cast_nullable_to_non_nullable
as UserRef?,consented: null == consented ? _self.consented : consented // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of ChangeCi
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get owner {
    if (_self.owner == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.owner!, (value) {
    return _then(_self.copyWith(owner: value));
  });
}
}


/// @nodoc
mixin _$Deviation {

 String get kind; bool get critical; String get messagePl;
/// Create a copy of Deviation
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DeviationCopyWith<Deviation> get copyWith => _$DeviationCopyWithImpl<Deviation>(this as Deviation, _$identity);

  /// Serializes this Deviation to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as Deviation;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Deviation&&(identical(other.kind, _this.kind) || other.kind == _this.kind)&&(identical(other.critical, _this.critical) || other.critical == _this.critical)&&(identical(other.messagePl, _this.messagePl) || other.messagePl == _this.messagePl));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as Deviation;
  return Object.hash(runtimeType,_this.kind,_this.critical,_this.messagePl);
}

@override
String toString() {
  final _this = this as Deviation;
  return 'Deviation(kind: ${_this.kind}, critical: ${_this.critical}, messagePl: ${_this.messagePl})';
}


}

/// @nodoc
abstract mixin class $DeviationCopyWith<$Res>  {
  factory $DeviationCopyWith(Deviation value, $Res Function(Deviation) _then) = _$DeviationCopyWithImpl;
@useResult
$Res call({
 String kind, bool critical, String messagePl
});




}
/// @nodoc
class _$DeviationCopyWithImpl<$Res>
    implements $DeviationCopyWith<$Res> {
  _$DeviationCopyWithImpl(this._self, this._then);

  final Deviation _self;
  final $Res Function(Deviation) _then;

/// Create a copy of Deviation
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? kind = null,Object? critical = null,Object? messagePl = null,}) {
  return _then(Deviation(
kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as String,critical: null == critical ? _self.critical : critical // ignore: cast_nullable_to_non_nullable
as bool,messagePl: null == messagePl ? _self.messagePl : messagePl // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

}


/// Adds pattern-matching-related methods to [Deviation].
extension DeviationPatterns on Deviation {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Deviation value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Deviation() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Deviation value)  $default,){
final _that = this;
switch (_that) {
case _Deviation():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Deviation value)?  $default,){
final _that = this;
switch (_that) {
case _Deviation() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String kind,  bool critical,  String messagePl)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Deviation() when $default != null:
return $default(_that.kind,_that.critical,_that.messagePl);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String kind,  bool critical,  String messagePl)  $default,) {final _that = this;
switch (_that) {
case _Deviation():
return $default(_that.kind,_that.critical,_that.messagePl);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String kind,  bool critical,  String messagePl)?  $default,) {final _that = this;
switch (_that) {
case _Deviation() when $default != null:
return $default(_that.kind,_that.critical,_that.messagePl);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Deviation implements Deviation {
  const _Deviation({required this.kind, this.critical = false, this.messagePl = ''});
  factory _Deviation.fromJson(Map<String, dynamic> json) => _$DeviationFromJson(json);

@override final  String kind;
@override@JsonKey() final  bool critical;
@override@JsonKey() final  String messagePl;

/// Create a copy of Deviation
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DeviationCopyWith<_Deviation> get copyWith => __$DeviationCopyWithImpl<_Deviation>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DeviationToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _Deviation&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.critical, critical) || other.critical == critical)&&(identical(other.messagePl, messagePl) || other.messagePl == messagePl));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,kind,critical,messagePl);
}

@override
String toString() {
    return 'Deviation(kind: $kind, critical: $critical, messagePl: $messagePl)';
}


}

/// @nodoc
abstract mixin class _$DeviationCopyWith<$Res> implements $DeviationCopyWith<$Res> {
  factory _$DeviationCopyWith(_Deviation value, $Res Function(_Deviation) _then) = __$DeviationCopyWithImpl;
@override @useResult
$Res call({
 String kind, bool critical, String messagePl
});




}
/// @nodoc
class __$DeviationCopyWithImpl<$Res>
    implements _$DeviationCopyWith<$Res> {
  __$DeviationCopyWithImpl(this._self, this._then);

  final _Deviation _self;
  final $Res Function(_Deviation) _then;

/// Create a copy of Deviation
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? kind = null,Object? critical = null,Object? messagePl = null,}) {
  return _then(_Deviation(
kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as String,critical: null == critical ? _self.critical : critical // ignore: cast_nullable_to_non_nullable
as bool,messagePl: null == messagePl ? _self.messagePl : messagePl // ignore: cast_nullable_to_non_nullable
as String,
  ));
}


}


/// @nodoc
mixin _$Consent {

 String get ciId; UserRef get owner; DateTime get consentedAt; bool get valid; bool get byRequesterOrAssignee;
/// Create a copy of Consent
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ConsentCopyWith<Consent> get copyWith => _$ConsentCopyWithImpl<Consent>(this as Consent, _$identity);

  /// Serializes this Consent to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as Consent;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Consent&&(identical(other.ciId, _this.ciId) || other.ciId == _this.ciId)&&(identical(other.owner, _this.owner) || other.owner == _this.owner)&&(identical(other.consentedAt, _this.consentedAt) || other.consentedAt == _this.consentedAt)&&(identical(other.valid, _this.valid) || other.valid == _this.valid)&&(identical(other.byRequesterOrAssignee, _this.byRequesterOrAssignee) || other.byRequesterOrAssignee == _this.byRequesterOrAssignee));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as Consent;
  return Object.hash(runtimeType,_this.ciId,_this.owner,_this.consentedAt,_this.valid,_this.byRequesterOrAssignee);
}

@override
String toString() {
  final _this = this as Consent;
  return 'Consent(ciId: ${_this.ciId}, owner: ${_this.owner}, consentedAt: ${_this.consentedAt}, valid: ${_this.valid}, byRequesterOrAssignee: ${_this.byRequesterOrAssignee})';
}


}

/// @nodoc
abstract mixin class $ConsentCopyWith<$Res>  {
  factory $ConsentCopyWith(Consent value, $Res Function(Consent) _then) = _$ConsentCopyWithImpl;
@useResult
$Res call({
 String ciId, UserRef owner, DateTime consentedAt, bool valid, bool byRequesterOrAssignee
});


$UserRefCopyWith<$Res> get owner;

}
/// @nodoc
class _$ConsentCopyWithImpl<$Res>
    implements $ConsentCopyWith<$Res> {
  _$ConsentCopyWithImpl(this._self, this._then);

  final Consent _self;
  final $Res Function(Consent) _then;

/// Create a copy of Consent
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? ciId = null,Object? owner = null,Object? consentedAt = null,Object? valid = null,Object? byRequesterOrAssignee = null,}) {
  return _then(Consent(
ciId: null == ciId ? _self.ciId : ciId // ignore: cast_nullable_to_non_nullable
as String,owner: null == owner ? _self.owner : owner // ignore: cast_nullable_to_non_nullable
as UserRef,consentedAt: null == consentedAt ? _self.consentedAt : consentedAt // ignore: cast_nullable_to_non_nullable
as DateTime,valid: null == valid ? _self.valid : valid // ignore: cast_nullable_to_non_nullable
as bool,byRequesterOrAssignee: null == byRequesterOrAssignee ? _self.byRequesterOrAssignee : byRequesterOrAssignee // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of Consent
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get owner {
  
  return $UserRefCopyWith<$Res>(_self.owner, (value) {
    return _then(_self.copyWith(owner: value));
  });
}
}


/// Adds pattern-matching-related methods to [Consent].
extension ConsentPatterns on Consent {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Consent value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Consent() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Consent value)  $default,){
final _that = this;
switch (_that) {
case _Consent():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Consent value)?  $default,){
final _that = this;
switch (_that) {
case _Consent() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String ciId,  UserRef owner,  DateTime consentedAt,  bool valid,  bool byRequesterOrAssignee)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Consent() when $default != null:
return $default(_that.ciId,_that.owner,_that.consentedAt,_that.valid,_that.byRequesterOrAssignee);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String ciId,  UserRef owner,  DateTime consentedAt,  bool valid,  bool byRequesterOrAssignee)  $default,) {final _that = this;
switch (_that) {
case _Consent():
return $default(_that.ciId,_that.owner,_that.consentedAt,_that.valid,_that.byRequesterOrAssignee);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String ciId,  UserRef owner,  DateTime consentedAt,  bool valid,  bool byRequesterOrAssignee)?  $default,) {final _that = this;
switch (_that) {
case _Consent() when $default != null:
return $default(_that.ciId,_that.owner,_that.consentedAt,_that.valid,_that.byRequesterOrAssignee);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Consent implements Consent {
  const _Consent({required this.ciId, required this.owner, required this.consentedAt, required this.valid, required this.byRequesterOrAssignee});
  factory _Consent.fromJson(Map<String, dynamic> json) => _$ConsentFromJson(json);

@override final  String ciId;
@override final  UserRef owner;
@override final  DateTime consentedAt;
@override final  bool valid;
@override final  bool byRequesterOrAssignee;

/// Create a copy of Consent
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ConsentCopyWith<_Consent> get copyWith => __$ConsentCopyWithImpl<_Consent>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ConsentToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _Consent&&(identical(other.ciId, ciId) || other.ciId == ciId)&&(identical(other.owner, owner) || other.owner == owner)&&(identical(other.consentedAt, consentedAt) || other.consentedAt == consentedAt)&&(identical(other.valid, valid) || other.valid == valid)&&(identical(other.byRequesterOrAssignee, byRequesterOrAssignee) || other.byRequesterOrAssignee == byRequesterOrAssignee));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,ciId,owner,consentedAt,valid,byRequesterOrAssignee);
}

@override
String toString() {
    return 'Consent(ciId: $ciId, owner: $owner, consentedAt: $consentedAt, valid: $valid, byRequesterOrAssignee: $byRequesterOrAssignee)';
}


}

/// @nodoc
abstract mixin class _$ConsentCopyWith<$Res> implements $ConsentCopyWith<$Res> {
  factory _$ConsentCopyWith(_Consent value, $Res Function(_Consent) _then) = __$ConsentCopyWithImpl;
@override @useResult
$Res call({
 String ciId, UserRef owner, DateTime consentedAt, bool valid, bool byRequesterOrAssignee
});


@override $UserRefCopyWith<$Res> get owner;

}
/// @nodoc
class __$ConsentCopyWithImpl<$Res>
    implements _$ConsentCopyWith<$Res> {
  __$ConsentCopyWithImpl(this._self, this._then);

  final _Consent _self;
  final $Res Function(_Consent) _then;

/// Create a copy of Consent
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? ciId = null,Object? owner = null,Object? consentedAt = null,Object? valid = null,Object? byRequesterOrAssignee = null,}) {
  return _then(_Consent(
ciId: null == ciId ? _self.ciId : ciId // ignore: cast_nullable_to_non_nullable
as String,owner: null == owner ? _self.owner : owner // ignore: cast_nullable_to_non_nullable
as UserRef,consentedAt: null == consentedAt ? _self.consentedAt : consentedAt // ignore: cast_nullable_to_non_nullable
as DateTime,valid: null == valid ? _self.valid : valid // ignore: cast_nullable_to_non_nullable
as bool,byRequesterOrAssignee: null == byRequesterOrAssignee ? _self.byRequesterOrAssignee : byRequesterOrAssignee // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of Consent
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get owner {
  
  return $UserRefCopyWith<$Res>(_self.owner, (value) {
    return _then(_self.copyWith(owner: value));
  });
}
}


/// @nodoc
mixin _$ChangeComment {

 String get id; UserRef get author; String get body; String? get action; DateTime get createdAt;
/// Create a copy of ChangeComment
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ChangeCommentCopyWith<ChangeComment> get copyWith => _$ChangeCommentCopyWithImpl<ChangeComment>(this as ChangeComment, _$identity);

  /// Serializes this ChangeComment to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ChangeComment;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ChangeComment&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.author, _this.author) || other.author == _this.author)&&(identical(other.body, _this.body) || other.body == _this.body)&&(identical(other.action, _this.action) || other.action == _this.action)&&(identical(other.createdAt, _this.createdAt) || other.createdAt == _this.createdAt));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ChangeComment;
  return Object.hash(runtimeType,_this.id,_this.author,_this.body,_this.action,_this.createdAt);
}

@override
String toString() {
  final _this = this as ChangeComment;
  return 'ChangeComment(id: ${_this.id}, author: ${_this.author}, body: ${_this.body}, action: ${_this.action}, createdAt: ${_this.createdAt})';
}


}

/// @nodoc
abstract mixin class $ChangeCommentCopyWith<$Res>  {
  factory $ChangeCommentCopyWith(ChangeComment value, $Res Function(ChangeComment) _then) = _$ChangeCommentCopyWithImpl;
@useResult
$Res call({
 String id, UserRef author, String body, String? action, DateTime createdAt
});


$UserRefCopyWith<$Res> get author;

}
/// @nodoc
class _$ChangeCommentCopyWithImpl<$Res>
    implements $ChangeCommentCopyWith<$Res> {
  _$ChangeCommentCopyWithImpl(this._self, this._then);

  final ChangeComment _self;
  final $Res Function(ChangeComment) _then;

/// Create a copy of ChangeComment
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? author = null,Object? body = null,Object? action = freezed,Object? createdAt = null,}) {
  return _then(ChangeComment(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,author: null == author ? _self.author : author // ignore: cast_nullable_to_non_nullable
as UserRef,body: null == body ? _self.body : body // ignore: cast_nullable_to_non_nullable
as String,action: freezed == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String?,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,
  ));
}
/// Create a copy of ChangeComment
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get author {
  
  return $UserRefCopyWith<$Res>(_self.author, (value) {
    return _then(_self.copyWith(author: value));
  });
}
}


/// Adds pattern-matching-related methods to [ChangeComment].
extension ChangeCommentPatterns on ChangeComment {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ChangeComment value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ChangeComment() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ChangeComment value)  $default,){
final _that = this;
switch (_that) {
case _ChangeComment():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ChangeComment value)?  $default,){
final _that = this;
switch (_that) {
case _ChangeComment() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  UserRef author,  String body,  String? action,  DateTime createdAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ChangeComment() when $default != null:
return $default(_that.id,_that.author,_that.body,_that.action,_that.createdAt);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  UserRef author,  String body,  String? action,  DateTime createdAt)  $default,) {final _that = this;
switch (_that) {
case _ChangeComment():
return $default(_that.id,_that.author,_that.body,_that.action,_that.createdAt);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  UserRef author,  String body,  String? action,  DateTime createdAt)?  $default,) {final _that = this;
switch (_that) {
case _ChangeComment() when $default != null:
return $default(_that.id,_that.author,_that.body,_that.action,_that.createdAt);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ChangeComment implements ChangeComment {
  const _ChangeComment({required this.id, required this.author, required this.body, this.action, required this.createdAt});
  factory _ChangeComment.fromJson(Map<String, dynamic> json) => _$ChangeCommentFromJson(json);

@override final  String id;
@override final  UserRef author;
@override final  String body;
@override final  String? action;
@override final  DateTime createdAt;

/// Create a copy of ChangeComment
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ChangeCommentCopyWith<_ChangeComment> get copyWith => __$ChangeCommentCopyWithImpl<_ChangeComment>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ChangeCommentToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ChangeComment&&(identical(other.id, id) || other.id == id)&&(identical(other.author, author) || other.author == author)&&(identical(other.body, body) || other.body == body)&&(identical(other.action, action) || other.action == action)&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,author,body,action,createdAt);
}

@override
String toString() {
    return 'ChangeComment(id: $id, author: $author, body: $body, action: $action, createdAt: $createdAt)';
}


}

/// @nodoc
abstract mixin class _$ChangeCommentCopyWith<$Res> implements $ChangeCommentCopyWith<$Res> {
  factory _$ChangeCommentCopyWith(_ChangeComment value, $Res Function(_ChangeComment) _then) = __$ChangeCommentCopyWithImpl;
@override @useResult
$Res call({
 String id, UserRef author, String body, String? action, DateTime createdAt
});


@override $UserRefCopyWith<$Res> get author;

}
/// @nodoc
class __$ChangeCommentCopyWithImpl<$Res>
    implements _$ChangeCommentCopyWith<$Res> {
  __$ChangeCommentCopyWithImpl(this._self, this._then);

  final _ChangeComment _self;
  final $Res Function(_ChangeComment) _then;

/// Create a copy of ChangeComment
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? author = null,Object? body = null,Object? action = freezed,Object? createdAt = null,}) {
  return _then(_ChangeComment(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,author: null == author ? _self.author : author // ignore: cast_nullable_to_non_nullable
as UserRef,body: null == body ? _self.body : body // ignore: cast_nullable_to_non_nullable
as String,action: freezed == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String?,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,
  ));
}

/// Create a copy of ChangeComment
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get author {
  
  return $UserRefCopyWith<$Res>(_self.author, (value) {
    return _then(_self.copyWith(author: value));
  });
}
}


/// @nodoc
mixin _$LinkedChange {

 String get id; String get number; String get status;
/// Create a copy of LinkedChange
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LinkedChangeCopyWith<LinkedChange> get copyWith => _$LinkedChangeCopyWithImpl<LinkedChange>(this as LinkedChange, _$identity);

  /// Serializes this LinkedChange to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as LinkedChange;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LinkedChange&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.number, _this.number) || other.number == _this.number)&&(identical(other.status, _this.status) || other.status == _this.status));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as LinkedChange;
  return Object.hash(runtimeType,_this.id,_this.number,_this.status);
}

@override
String toString() {
  final _this = this as LinkedChange;
  return 'LinkedChange(id: ${_this.id}, number: ${_this.number}, status: ${_this.status})';
}


}

/// @nodoc
abstract mixin class $LinkedChangeCopyWith<$Res>  {
  factory $LinkedChangeCopyWith(LinkedChange value, $Res Function(LinkedChange) _then) = _$LinkedChangeCopyWithImpl;
@useResult
$Res call({
 String id, String number, String status
});




}
/// @nodoc
class _$LinkedChangeCopyWithImpl<$Res>
    implements $LinkedChangeCopyWith<$Res> {
  _$LinkedChangeCopyWithImpl(this._self, this._then);

  final LinkedChange _self;
  final $Res Function(LinkedChange) _then;

/// Create a copy of LinkedChange
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? number = null,Object? status = null,}) {
  return _then(LinkedChange(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,number: null == number ? _self.number : number // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

}


/// Adds pattern-matching-related methods to [LinkedChange].
extension LinkedChangePatterns on LinkedChange {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LinkedChange value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LinkedChange() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LinkedChange value)  $default,){
final _that = this;
switch (_that) {
case _LinkedChange():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LinkedChange value)?  $default,){
final _that = this;
switch (_that) {
case _LinkedChange() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String number,  String status)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LinkedChange() when $default != null:
return $default(_that.id,_that.number,_that.status);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String number,  String status)  $default,) {final _that = this;
switch (_that) {
case _LinkedChange():
return $default(_that.id,_that.number,_that.status);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String number,  String status)?  $default,) {final _that = this;
switch (_that) {
case _LinkedChange() when $default != null:
return $default(_that.id,_that.number,_that.status);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _LinkedChange extends LinkedChange {
  const _LinkedChange({required this.id, required this.number, required this.status}): super._();
  factory _LinkedChange.fromJson(Map<String, dynamic> json) => _$LinkedChangeFromJson(json);

@override final  String id;
@override final  String number;
@override final  String status;

/// Create a copy of LinkedChange
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LinkedChangeCopyWith<_LinkedChange> get copyWith => __$LinkedChangeCopyWithImpl<_LinkedChange>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$LinkedChangeToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _LinkedChange&&(identical(other.id, id) || other.id == id)&&(identical(other.number, number) || other.number == number)&&(identical(other.status, status) || other.status == status));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,number,status);
}

@override
String toString() {
    return 'LinkedChange(id: $id, number: $number, status: $status)';
}


}

/// @nodoc
abstract mixin class _$LinkedChangeCopyWith<$Res> implements $LinkedChangeCopyWith<$Res> {
  factory _$LinkedChangeCopyWith(_LinkedChange value, $Res Function(_LinkedChange) _then) = __$LinkedChangeCopyWithImpl;
@override @useResult
$Res call({
 String id, String number, String status
});




}
/// @nodoc
class __$LinkedChangeCopyWithImpl<$Res>
    implements _$LinkedChangeCopyWith<$Res> {
  __$LinkedChangeCopyWithImpl(this._self, this._then);

  final _LinkedChange _self;
  final $Res Function(_LinkedChange) _then;

/// Create a copy of LinkedChange
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? number = null,Object? status = null,}) {
  return _then(_LinkedChange(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,number: null == number ? _self.number : number // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,
  ));
}


}


/// @nodoc
mixin _$Change {

 String get id; String get companyId; String get number; String? get title; String get status; String? get changeType; String? get risk; CategoryRef? get category; CategoryRef? get subcategory; List<ChangeCi> get ci; UserRef get requestedBy; UserRef? get assignee; UserRef? get approver; UserRef? get verifier; DateTime? get windowStart; DateTime? get windowEnd; DateTime? get approvedAt; UserRef? get approvedBy; bool get autoApproved; DateTime? get implementedAt; DateTime? get verifiedAt; DateTime? get rejectedAt; List<Deviation> get deviations; DateTime get createdAt; DateTime get updatedAt; String? get description; String? get implementationPlan; String? get rollbackPlan; String? get impact; String? get requirementRef; String? get ticketRef; String? get supersedesChangeId; String? get supersedesNumber; List<LinkedChange> get supersededBy; int get version; List<String> get allowedActions; List<String> get editableFields;@JsonKey(unknownEnumValue: ChangeAccess.unknown) ChangeAccess get access; String? get suggestedApproverId; List<Consent> get consents; List<ChangeComment> get comments;
/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ChangeCopyWith<Change> get copyWith => _$ChangeCopyWithImpl<Change>(this as Change, _$identity);

  /// Serializes this Change to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as Change;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Change&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.companyId, _this.companyId) || other.companyId == _this.companyId)&&(identical(other.number, _this.number) || other.number == _this.number)&&(identical(other.title, _this.title) || other.title == _this.title)&&(identical(other.status, _this.status) || other.status == _this.status)&&(identical(other.changeType, _this.changeType) || other.changeType == _this.changeType)&&(identical(other.risk, _this.risk) || other.risk == _this.risk)&&(identical(other.category, _this.category) || other.category == _this.category)&&(identical(other.subcategory, _this.subcategory) || other.subcategory == _this.subcategory)&&const DeepCollectionEquality().equals(other.ci, _this.ci)&&(identical(other.requestedBy, _this.requestedBy) || other.requestedBy == _this.requestedBy)&&(identical(other.assignee, _this.assignee) || other.assignee == _this.assignee)&&(identical(other.approver, _this.approver) || other.approver == _this.approver)&&(identical(other.verifier, _this.verifier) || other.verifier == _this.verifier)&&(identical(other.windowStart, _this.windowStart) || other.windowStart == _this.windowStart)&&(identical(other.windowEnd, _this.windowEnd) || other.windowEnd == _this.windowEnd)&&(identical(other.approvedAt, _this.approvedAt) || other.approvedAt == _this.approvedAt)&&(identical(other.approvedBy, _this.approvedBy) || other.approvedBy == _this.approvedBy)&&(identical(other.autoApproved, _this.autoApproved) || other.autoApproved == _this.autoApproved)&&(identical(other.implementedAt, _this.implementedAt) || other.implementedAt == _this.implementedAt)&&(identical(other.verifiedAt, _this.verifiedAt) || other.verifiedAt == _this.verifiedAt)&&(identical(other.rejectedAt, _this.rejectedAt) || other.rejectedAt == _this.rejectedAt)&&const DeepCollectionEquality().equals(other.deviations, _this.deviations)&&(identical(other.createdAt, _this.createdAt) || other.createdAt == _this.createdAt)&&(identical(other.updatedAt, _this.updatedAt) || other.updatedAt == _this.updatedAt)&&(identical(other.description, _this.description) || other.description == _this.description)&&(identical(other.implementationPlan, _this.implementationPlan) || other.implementationPlan == _this.implementationPlan)&&(identical(other.rollbackPlan, _this.rollbackPlan) || other.rollbackPlan == _this.rollbackPlan)&&(identical(other.impact, _this.impact) || other.impact == _this.impact)&&(identical(other.requirementRef, _this.requirementRef) || other.requirementRef == _this.requirementRef)&&(identical(other.ticketRef, _this.ticketRef) || other.ticketRef == _this.ticketRef)&&(identical(other.supersedesChangeId, _this.supersedesChangeId) || other.supersedesChangeId == _this.supersedesChangeId)&&(identical(other.supersedesNumber, _this.supersedesNumber) || other.supersedesNumber == _this.supersedesNumber)&&const DeepCollectionEquality().equals(other.supersededBy, _this.supersededBy)&&(identical(other.version, _this.version) || other.version == _this.version)&&const DeepCollectionEquality().equals(other.allowedActions, _this.allowedActions)&&const DeepCollectionEquality().equals(other.editableFields, _this.editableFields)&&(identical(other.access, _this.access) || other.access == _this.access)&&(identical(other.suggestedApproverId, _this.suggestedApproverId) || other.suggestedApproverId == _this.suggestedApproverId)&&const DeepCollectionEquality().equals(other.consents, _this.consents)&&const DeepCollectionEquality().equals(other.comments, _this.comments));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as Change;
  return Object.hashAll([runtimeType,_this.id,_this.companyId,_this.number,_this.title,_this.status,_this.changeType,_this.risk,_this.category,_this.subcategory,const DeepCollectionEquality().hash(_this.ci),_this.requestedBy,_this.assignee,_this.approver,_this.verifier,_this.windowStart,_this.windowEnd,_this.approvedAt,_this.approvedBy,_this.autoApproved,_this.implementedAt,_this.verifiedAt,_this.rejectedAt,const DeepCollectionEquality().hash(_this.deviations),_this.createdAt,_this.updatedAt,_this.description,_this.implementationPlan,_this.rollbackPlan,_this.impact,_this.requirementRef,_this.ticketRef,_this.supersedesChangeId,_this.supersedesNumber,const DeepCollectionEquality().hash(_this.supersededBy),_this.version,const DeepCollectionEquality().hash(_this.allowedActions),const DeepCollectionEquality().hash(_this.editableFields),_this.access,_this.suggestedApproverId,const DeepCollectionEquality().hash(_this.consents),const DeepCollectionEquality().hash(_this.comments)]);
}

@override
String toString() {
  final _this = this as Change;
  return 'Change(id: ${_this.id}, companyId: ${_this.companyId}, number: ${_this.number}, title: ${_this.title}, status: ${_this.status}, changeType: ${_this.changeType}, risk: ${_this.risk}, category: ${_this.category}, subcategory: ${_this.subcategory}, ci: ${_this.ci}, requestedBy: ${_this.requestedBy}, assignee: ${_this.assignee}, approver: ${_this.approver}, verifier: ${_this.verifier}, windowStart: ${_this.windowStart}, windowEnd: ${_this.windowEnd}, approvedAt: ${_this.approvedAt}, approvedBy: ${_this.approvedBy}, autoApproved: ${_this.autoApproved}, implementedAt: ${_this.implementedAt}, verifiedAt: ${_this.verifiedAt}, rejectedAt: ${_this.rejectedAt}, deviations: ${_this.deviations}, createdAt: ${_this.createdAt}, updatedAt: ${_this.updatedAt}, description: ${_this.description}, implementationPlan: ${_this.implementationPlan}, rollbackPlan: ${_this.rollbackPlan}, impact: ${_this.impact}, requirementRef: ${_this.requirementRef}, ticketRef: ${_this.ticketRef}, supersedesChangeId: ${_this.supersedesChangeId}, supersedesNumber: ${_this.supersedesNumber}, supersededBy: ${_this.supersededBy}, version: ${_this.version}, allowedActions: ${_this.allowedActions}, editableFields: ${_this.editableFields}, access: ${_this.access}, suggestedApproverId: ${_this.suggestedApproverId}, consents: ${_this.consents}, comments: ${_this.comments})';
}


}

/// @nodoc
abstract mixin class $ChangeCopyWith<$Res>  {
  factory $ChangeCopyWith(Change value, $Res Function(Change) _then) = _$ChangeCopyWithImpl;
@useResult
$Res call({
 String id, String companyId, String number, String? title, String status, String? changeType, String? risk, CategoryRef? category, CategoryRef? subcategory, List<ChangeCi> ci, UserRef requestedBy, UserRef? assignee, UserRef? approver, UserRef? verifier, DateTime? windowStart, DateTime? windowEnd, DateTime? approvedAt, UserRef? approvedBy, bool autoApproved, DateTime? implementedAt, DateTime? verifiedAt, DateTime? rejectedAt, List<Deviation> deviations, DateTime createdAt, DateTime updatedAt, String? description, String? implementationPlan, String? rollbackPlan, String? impact, String? requirementRef, String? ticketRef, String? supersedesChangeId, String? supersedesNumber, List<LinkedChange> supersededBy, int version, List<String> allowedActions, List<String> editableFields,@JsonKey(unknownEnumValue: ChangeAccess.unknown) ChangeAccess access, String? suggestedApproverId, List<Consent> consents, List<ChangeComment> comments
});


$CategoryRefCopyWith<$Res>? get category;$CategoryRefCopyWith<$Res>? get subcategory;$UserRefCopyWith<$Res> get requestedBy;$UserRefCopyWith<$Res>? get assignee;$UserRefCopyWith<$Res>? get approver;$UserRefCopyWith<$Res>? get verifier;$UserRefCopyWith<$Res>? get approvedBy;

}
/// @nodoc
class _$ChangeCopyWithImpl<$Res>
    implements $ChangeCopyWith<$Res> {
  _$ChangeCopyWithImpl(this._self, this._then);

  final Change _self;
  final $Res Function(Change) _then;

/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? companyId = null,Object? number = null,Object? title = freezed,Object? status = null,Object? changeType = freezed,Object? risk = freezed,Object? category = freezed,Object? subcategory = freezed,Object? ci = null,Object? requestedBy = null,Object? assignee = freezed,Object? approver = freezed,Object? verifier = freezed,Object? windowStart = freezed,Object? windowEnd = freezed,Object? approvedAt = freezed,Object? approvedBy = freezed,Object? autoApproved = null,Object? implementedAt = freezed,Object? verifiedAt = freezed,Object? rejectedAt = freezed,Object? deviations = null,Object? createdAt = null,Object? updatedAt = null,Object? description = freezed,Object? implementationPlan = freezed,Object? rollbackPlan = freezed,Object? impact = freezed,Object? requirementRef = freezed,Object? ticketRef = freezed,Object? supersedesChangeId = freezed,Object? supersedesNumber = freezed,Object? supersededBy = null,Object? version = null,Object? allowedActions = null,Object? editableFields = null,Object? access = null,Object? suggestedApproverId = freezed,Object? consents = null,Object? comments = null,}) {
  return _then(Change(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,companyId: null == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String,number: null == number ? _self.number : number // ignore: cast_nullable_to_non_nullable
as String,title: freezed == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String?,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,changeType: freezed == changeType ? _self.changeType : changeType // ignore: cast_nullable_to_non_nullable
as String?,risk: freezed == risk ? _self.risk : risk // ignore: cast_nullable_to_non_nullable
as String?,category: freezed == category ? _self.category : category // ignore: cast_nullable_to_non_nullable
as CategoryRef?,subcategory: freezed == subcategory ? _self.subcategory : subcategory // ignore: cast_nullable_to_non_nullable
as CategoryRef?,ci: null == ci ? _self.ci : ci // ignore: cast_nullable_to_non_nullable
as List<ChangeCi>,requestedBy: null == requestedBy ? _self.requestedBy : requestedBy // ignore: cast_nullable_to_non_nullable
as UserRef,assignee: freezed == assignee ? _self.assignee : assignee // ignore: cast_nullable_to_non_nullable
as UserRef?,approver: freezed == approver ? _self.approver : approver // ignore: cast_nullable_to_non_nullable
as UserRef?,verifier: freezed == verifier ? _self.verifier : verifier // ignore: cast_nullable_to_non_nullable
as UserRef?,windowStart: freezed == windowStart ? _self.windowStart : windowStart // ignore: cast_nullable_to_non_nullable
as DateTime?,windowEnd: freezed == windowEnd ? _self.windowEnd : windowEnd // ignore: cast_nullable_to_non_nullable
as DateTime?,approvedAt: freezed == approvedAt ? _self.approvedAt : approvedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,approvedBy: freezed == approvedBy ? _self.approvedBy : approvedBy // ignore: cast_nullable_to_non_nullable
as UserRef?,autoApproved: null == autoApproved ? _self.autoApproved : autoApproved // ignore: cast_nullable_to_non_nullable
as bool,implementedAt: freezed == implementedAt ? _self.implementedAt : implementedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,verifiedAt: freezed == verifiedAt ? _self.verifiedAt : verifiedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,rejectedAt: freezed == rejectedAt ? _self.rejectedAt : rejectedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,deviations: null == deviations ? _self.deviations : deviations // ignore: cast_nullable_to_non_nullable
as List<Deviation>,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,updatedAt: null == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,implementationPlan: freezed == implementationPlan ? _self.implementationPlan : implementationPlan // ignore: cast_nullable_to_non_nullable
as String?,rollbackPlan: freezed == rollbackPlan ? _self.rollbackPlan : rollbackPlan // ignore: cast_nullable_to_non_nullable
as String?,impact: freezed == impact ? _self.impact : impact // ignore: cast_nullable_to_non_nullable
as String?,requirementRef: freezed == requirementRef ? _self.requirementRef : requirementRef // ignore: cast_nullable_to_non_nullable
as String?,ticketRef: freezed == ticketRef ? _self.ticketRef : ticketRef // ignore: cast_nullable_to_non_nullable
as String?,supersedesChangeId: freezed == supersedesChangeId ? _self.supersedesChangeId : supersedesChangeId // ignore: cast_nullable_to_non_nullable
as String?,supersedesNumber: freezed == supersedesNumber ? _self.supersedesNumber : supersedesNumber // ignore: cast_nullable_to_non_nullable
as String?,supersededBy: null == supersededBy ? _self.supersededBy : supersededBy // ignore: cast_nullable_to_non_nullable
as List<LinkedChange>,version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,allowedActions: null == allowedActions ? _self.allowedActions : allowedActions // ignore: cast_nullable_to_non_nullable
as List<String>,editableFields: null == editableFields ? _self.editableFields : editableFields // ignore: cast_nullable_to_non_nullable
as List<String>,access: null == access ? _self.access : access // ignore: cast_nullable_to_non_nullable
as ChangeAccess,suggestedApproverId: freezed == suggestedApproverId ? _self.suggestedApproverId : suggestedApproverId // ignore: cast_nullable_to_non_nullable
as String?,consents: null == consents ? _self.consents : consents // ignore: cast_nullable_to_non_nullable
as List<Consent>,comments: null == comments ? _self.comments : comments // ignore: cast_nullable_to_non_nullable
as List<ChangeComment>,
  ));
}
/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$CategoryRefCopyWith<$Res>? get category {
    if (_self.category == null) {
    return null;
  }

  return $CategoryRefCopyWith<$Res>(_self.category!, (value) {
    return _then(_self.copyWith(category: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$CategoryRefCopyWith<$Res>? get subcategory {
    if (_self.subcategory == null) {
    return null;
  }

  return $CategoryRefCopyWith<$Res>(_self.subcategory!, (value) {
    return _then(_self.copyWith(subcategory: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get requestedBy {
  
  return $UserRefCopyWith<$Res>(_self.requestedBy, (value) {
    return _then(_self.copyWith(requestedBy: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get assignee {
    if (_self.assignee == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.assignee!, (value) {
    return _then(_self.copyWith(assignee: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get approver {
    if (_self.approver == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.approver!, (value) {
    return _then(_self.copyWith(approver: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get verifier {
    if (_self.verifier == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.verifier!, (value) {
    return _then(_self.copyWith(verifier: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get approvedBy {
    if (_self.approvedBy == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.approvedBy!, (value) {
    return _then(_self.copyWith(approvedBy: value));
  });
}
}


/// Adds pattern-matching-related methods to [Change].
extension ChangePatterns on Change {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Change value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Change() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Change value)  $default,){
final _that = this;
switch (_that) {
case _Change():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Change value)?  $default,){
final _that = this;
switch (_that) {
case _Change() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String companyId,  String number,  String? title,  String status,  String? changeType,  String? risk,  CategoryRef? category,  CategoryRef? subcategory,  List<ChangeCi> ci,  UserRef requestedBy,  UserRef? assignee,  UserRef? approver,  UserRef? verifier,  DateTime? windowStart,  DateTime? windowEnd,  DateTime? approvedAt,  UserRef? approvedBy,  bool autoApproved,  DateTime? implementedAt,  DateTime? verifiedAt,  DateTime? rejectedAt,  List<Deviation> deviations,  DateTime createdAt,  DateTime updatedAt,  String? description,  String? implementationPlan,  String? rollbackPlan,  String? impact,  String? requirementRef,  String? ticketRef,  String? supersedesChangeId,  String? supersedesNumber,  List<LinkedChange> supersededBy,  int version,  List<String> allowedActions,  List<String> editableFields, @JsonKey(unknownEnumValue: ChangeAccess.unknown)  ChangeAccess access,  String? suggestedApproverId,  List<Consent> consents,  List<ChangeComment> comments)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Change() when $default != null:
return $default(_that.id,_that.companyId,_that.number,_that.title,_that.status,_that.changeType,_that.risk,_that.category,_that.subcategory,_that.ci,_that.requestedBy,_that.assignee,_that.approver,_that.verifier,_that.windowStart,_that.windowEnd,_that.approvedAt,_that.approvedBy,_that.autoApproved,_that.implementedAt,_that.verifiedAt,_that.rejectedAt,_that.deviations,_that.createdAt,_that.updatedAt,_that.description,_that.implementationPlan,_that.rollbackPlan,_that.impact,_that.requirementRef,_that.ticketRef,_that.supersedesChangeId,_that.supersedesNumber,_that.supersededBy,_that.version,_that.allowedActions,_that.editableFields,_that.access,_that.suggestedApproverId,_that.consents,_that.comments);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String companyId,  String number,  String? title,  String status,  String? changeType,  String? risk,  CategoryRef? category,  CategoryRef? subcategory,  List<ChangeCi> ci,  UserRef requestedBy,  UserRef? assignee,  UserRef? approver,  UserRef? verifier,  DateTime? windowStart,  DateTime? windowEnd,  DateTime? approvedAt,  UserRef? approvedBy,  bool autoApproved,  DateTime? implementedAt,  DateTime? verifiedAt,  DateTime? rejectedAt,  List<Deviation> deviations,  DateTime createdAt,  DateTime updatedAt,  String? description,  String? implementationPlan,  String? rollbackPlan,  String? impact,  String? requirementRef,  String? ticketRef,  String? supersedesChangeId,  String? supersedesNumber,  List<LinkedChange> supersededBy,  int version,  List<String> allowedActions,  List<String> editableFields, @JsonKey(unknownEnumValue: ChangeAccess.unknown)  ChangeAccess access,  String? suggestedApproverId,  List<Consent> consents,  List<ChangeComment> comments)  $default,) {final _that = this;
switch (_that) {
case _Change():
return $default(_that.id,_that.companyId,_that.number,_that.title,_that.status,_that.changeType,_that.risk,_that.category,_that.subcategory,_that.ci,_that.requestedBy,_that.assignee,_that.approver,_that.verifier,_that.windowStart,_that.windowEnd,_that.approvedAt,_that.approvedBy,_that.autoApproved,_that.implementedAt,_that.verifiedAt,_that.rejectedAt,_that.deviations,_that.createdAt,_that.updatedAt,_that.description,_that.implementationPlan,_that.rollbackPlan,_that.impact,_that.requirementRef,_that.ticketRef,_that.supersedesChangeId,_that.supersedesNumber,_that.supersededBy,_that.version,_that.allowedActions,_that.editableFields,_that.access,_that.suggestedApproverId,_that.consents,_that.comments);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String companyId,  String number,  String? title,  String status,  String? changeType,  String? risk,  CategoryRef? category,  CategoryRef? subcategory,  List<ChangeCi> ci,  UserRef requestedBy,  UserRef? assignee,  UserRef? approver,  UserRef? verifier,  DateTime? windowStart,  DateTime? windowEnd,  DateTime? approvedAt,  UserRef? approvedBy,  bool autoApproved,  DateTime? implementedAt,  DateTime? verifiedAt,  DateTime? rejectedAt,  List<Deviation> deviations,  DateTime createdAt,  DateTime updatedAt,  String? description,  String? implementationPlan,  String? rollbackPlan,  String? impact,  String? requirementRef,  String? ticketRef,  String? supersedesChangeId,  String? supersedesNumber,  List<LinkedChange> supersededBy,  int version,  List<String> allowedActions,  List<String> editableFields, @JsonKey(unknownEnumValue: ChangeAccess.unknown)  ChangeAccess access,  String? suggestedApproverId,  List<Consent> consents,  List<ChangeComment> comments)?  $default,) {final _that = this;
switch (_that) {
case _Change() when $default != null:
return $default(_that.id,_that.companyId,_that.number,_that.title,_that.status,_that.changeType,_that.risk,_that.category,_that.subcategory,_that.ci,_that.requestedBy,_that.assignee,_that.approver,_that.verifier,_that.windowStart,_that.windowEnd,_that.approvedAt,_that.approvedBy,_that.autoApproved,_that.implementedAt,_that.verifiedAt,_that.rejectedAt,_that.deviations,_that.createdAt,_that.updatedAt,_that.description,_that.implementationPlan,_that.rollbackPlan,_that.impact,_that.requirementRef,_that.ticketRef,_that.supersedesChangeId,_that.supersedesNumber,_that.supersededBy,_that.version,_that.allowedActions,_that.editableFields,_that.access,_that.suggestedApproverId,_that.consents,_that.comments);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Change extends Change {
  const _Change({required this.id, required this.companyId, required this.number, this.title, required this.status, this.changeType, this.risk, this.category, this.subcategory,  List<ChangeCi> ci = const <ChangeCi>[], required this.requestedBy, this.assignee, this.approver, this.verifier, this.windowStart, this.windowEnd, this.approvedAt, this.approvedBy, this.autoApproved = false, this.implementedAt, this.verifiedAt, this.rejectedAt,  List<Deviation> deviations = const <Deviation>[], required this.createdAt, required this.updatedAt, this.description, this.implementationPlan, this.rollbackPlan, this.impact, this.requirementRef, this.ticketRef, this.supersedesChangeId, this.supersedesNumber,  List<LinkedChange> supersededBy = const <LinkedChange>[], this.version = 0,  List<String> allowedActions = const <String>[],  List<String> editableFields = const <String>[], @JsonKey(unknownEnumValue: ChangeAccess.unknown) this.access = ChangeAccess.unknown, this.suggestedApproverId,  List<Consent> consents = const <Consent>[],  List<ChangeComment> comments = const <ChangeComment>[]}): _ci = ci,_deviations = deviations,_supersededBy = supersededBy,_allowedActions = allowedActions,_editableFields = editableFields,_consents = consents,_comments = comments,super._();
  factory _Change.fromJson(Map<String, dynamic> json) => _$ChangeFromJson(json);

@override final  String id;
@override final  String companyId;
@override final  String number;
@override final  String? title;
@override final  String status;
@override final  String? changeType;
@override final  String? risk;
@override final  CategoryRef? category;
@override final  CategoryRef? subcategory;
 final  List<ChangeCi> _ci;
@override@JsonKey() List<ChangeCi> get ci {
  if (_ci is EqualUnmodifiableListView) return _ci;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_ci);
}

@override final  UserRef requestedBy;
@override final  UserRef? assignee;
@override final  UserRef? approver;
@override final  UserRef? verifier;
@override final  DateTime? windowStart;
@override final  DateTime? windowEnd;
@override final  DateTime? approvedAt;
@override final  UserRef? approvedBy;
@override@JsonKey() final  bool autoApproved;
@override final  DateTime? implementedAt;
@override final  DateTime? verifiedAt;
@override final  DateTime? rejectedAt;
 final  List<Deviation> _deviations;
@override@JsonKey() List<Deviation> get deviations {
  if (_deviations is EqualUnmodifiableListView) return _deviations;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_deviations);
}

@override final  DateTime createdAt;
@override final  DateTime updatedAt;
@override final  String? description;
@override final  String? implementationPlan;
@override final  String? rollbackPlan;
@override final  String? impact;
@override final  String? requirementRef;
@override final  String? ticketRef;
@override final  String? supersedesChangeId;
@override final  String? supersedesNumber;
 final  List<LinkedChange> _supersededBy;
@override@JsonKey() List<LinkedChange> get supersededBy {
  if (_supersededBy is EqualUnmodifiableListView) return _supersededBy;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_supersededBy);
}

@override@JsonKey() final  int version;
 final  List<String> _allowedActions;
@override@JsonKey() List<String> get allowedActions {
  if (_allowedActions is EqualUnmodifiableListView) return _allowedActions;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_allowedActions);
}

 final  List<String> _editableFields;
@override@JsonKey() List<String> get editableFields {
  if (_editableFields is EqualUnmodifiableListView) return _editableFields;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_editableFields);
}

@override@JsonKey(unknownEnumValue: ChangeAccess.unknown) final  ChangeAccess access;
@override final  String? suggestedApproverId;
 final  List<Consent> _consents;
@override@JsonKey() List<Consent> get consents {
  if (_consents is EqualUnmodifiableListView) return _consents;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_consents);
}

 final  List<ChangeComment> _comments;
@override@JsonKey() List<ChangeComment> get comments {
  if (_comments is EqualUnmodifiableListView) return _comments;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_comments);
}


/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ChangeCopyWith<_Change> get copyWith => __$ChangeCopyWithImpl<_Change>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ChangeToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _Change&&(identical(other.id, id) || other.id == id)&&(identical(other.companyId, companyId) || other.companyId == companyId)&&(identical(other.number, number) || other.number == number)&&(identical(other.title, title) || other.title == title)&&(identical(other.status, status) || other.status == status)&&(identical(other.changeType, changeType) || other.changeType == changeType)&&(identical(other.risk, risk) || other.risk == risk)&&(identical(other.category, category) || other.category == category)&&(identical(other.subcategory, subcategory) || other.subcategory == subcategory)&&const DeepCollectionEquality().equals(other.ci, _ci)&&(identical(other.requestedBy, requestedBy) || other.requestedBy == requestedBy)&&(identical(other.assignee, assignee) || other.assignee == assignee)&&(identical(other.approver, approver) || other.approver == approver)&&(identical(other.verifier, verifier) || other.verifier == verifier)&&(identical(other.windowStart, windowStart) || other.windowStart == windowStart)&&(identical(other.windowEnd, windowEnd) || other.windowEnd == windowEnd)&&(identical(other.approvedAt, approvedAt) || other.approvedAt == approvedAt)&&(identical(other.approvedBy, approvedBy) || other.approvedBy == approvedBy)&&(identical(other.autoApproved, autoApproved) || other.autoApproved == autoApproved)&&(identical(other.implementedAt, implementedAt) || other.implementedAt == implementedAt)&&(identical(other.verifiedAt, verifiedAt) || other.verifiedAt == verifiedAt)&&(identical(other.rejectedAt, rejectedAt) || other.rejectedAt == rejectedAt)&&const DeepCollectionEquality().equals(other.deviations, _deviations)&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt)&&(identical(other.updatedAt, updatedAt) || other.updatedAt == updatedAt)&&(identical(other.description, description) || other.description == description)&&(identical(other.implementationPlan, implementationPlan) || other.implementationPlan == implementationPlan)&&(identical(other.rollbackPlan, rollbackPlan) || other.rollbackPlan == rollbackPlan)&&(identical(other.impact, impact) || other.impact == impact)&&(identical(other.requirementRef, requirementRef) || other.requirementRef == requirementRef)&&(identical(other.ticketRef, ticketRef) || other.ticketRef == ticketRef)&&(identical(other.supersedesChangeId, supersedesChangeId) || other.supersedesChangeId == supersedesChangeId)&&(identical(other.supersedesNumber, supersedesNumber) || other.supersedesNumber == supersedesNumber)&&const DeepCollectionEquality().equals(other.supersededBy, _supersededBy)&&(identical(other.version, version) || other.version == version)&&const DeepCollectionEquality().equals(other.allowedActions, _allowedActions)&&const DeepCollectionEquality().equals(other.editableFields, _editableFields)&&(identical(other.access, access) || other.access == access)&&(identical(other.suggestedApproverId, suggestedApproverId) || other.suggestedApproverId == suggestedApproverId)&&const DeepCollectionEquality().equals(other.consents, _consents)&&const DeepCollectionEquality().equals(other.comments, _comments));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hashAll([runtimeType,id,companyId,number,title,status,changeType,risk,category,subcategory,const DeepCollectionEquality().hash(_ci),requestedBy,assignee,approver,verifier,windowStart,windowEnd,approvedAt,approvedBy,autoApproved,implementedAt,verifiedAt,rejectedAt,const DeepCollectionEquality().hash(_deviations),createdAt,updatedAt,description,implementationPlan,rollbackPlan,impact,requirementRef,ticketRef,supersedesChangeId,supersedesNumber,const DeepCollectionEquality().hash(_supersededBy),version,const DeepCollectionEquality().hash(_allowedActions),const DeepCollectionEquality().hash(_editableFields),access,suggestedApproverId,const DeepCollectionEquality().hash(_consents),const DeepCollectionEquality().hash(_comments)]);
}

@override
String toString() {
    return 'Change(id: $id, companyId: $companyId, number: $number, title: $title, status: $status, changeType: $changeType, risk: $risk, category: $category, subcategory: $subcategory, ci: $ci, requestedBy: $requestedBy, assignee: $assignee, approver: $approver, verifier: $verifier, windowStart: $windowStart, windowEnd: $windowEnd, approvedAt: $approvedAt, approvedBy: $approvedBy, autoApproved: $autoApproved, implementedAt: $implementedAt, verifiedAt: $verifiedAt, rejectedAt: $rejectedAt, deviations: $deviations, createdAt: $createdAt, updatedAt: $updatedAt, description: $description, implementationPlan: $implementationPlan, rollbackPlan: $rollbackPlan, impact: $impact, requirementRef: $requirementRef, ticketRef: $ticketRef, supersedesChangeId: $supersedesChangeId, supersedesNumber: $supersedesNumber, supersededBy: $supersededBy, version: $version, allowedActions: $allowedActions, editableFields: $editableFields, access: $access, suggestedApproverId: $suggestedApproverId, consents: $consents, comments: $comments)';
}


}

/// @nodoc
abstract mixin class _$ChangeCopyWith<$Res> implements $ChangeCopyWith<$Res> {
  factory _$ChangeCopyWith(_Change value, $Res Function(_Change) _then) = __$ChangeCopyWithImpl;
@override @useResult
$Res call({
 String id, String companyId, String number, String? title, String status, String? changeType, String? risk, CategoryRef? category, CategoryRef? subcategory, List<ChangeCi> ci, UserRef requestedBy, UserRef? assignee, UserRef? approver, UserRef? verifier, DateTime? windowStart, DateTime? windowEnd, DateTime? approvedAt, UserRef? approvedBy, bool autoApproved, DateTime? implementedAt, DateTime? verifiedAt, DateTime? rejectedAt, List<Deviation> deviations, DateTime createdAt, DateTime updatedAt, String? description, String? implementationPlan, String? rollbackPlan, String? impact, String? requirementRef, String? ticketRef, String? supersedesChangeId, String? supersedesNumber, List<LinkedChange> supersededBy, int version, List<String> allowedActions, List<String> editableFields,@JsonKey(unknownEnumValue: ChangeAccess.unknown) ChangeAccess access, String? suggestedApproverId, List<Consent> consents, List<ChangeComment> comments
});


@override $CategoryRefCopyWith<$Res>? get category;@override $CategoryRefCopyWith<$Res>? get subcategory;@override $UserRefCopyWith<$Res> get requestedBy;@override $UserRefCopyWith<$Res>? get assignee;@override $UserRefCopyWith<$Res>? get approver;@override $UserRefCopyWith<$Res>? get verifier;@override $UserRefCopyWith<$Res>? get approvedBy;

}
/// @nodoc
class __$ChangeCopyWithImpl<$Res>
    implements _$ChangeCopyWith<$Res> {
  __$ChangeCopyWithImpl(this._self, this._then);

  final _Change _self;
  final $Res Function(_Change) _then;

/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? companyId = null,Object? number = null,Object? title = freezed,Object? status = null,Object? changeType = freezed,Object? risk = freezed,Object? category = freezed,Object? subcategory = freezed,Object? ci = null,Object? requestedBy = null,Object? assignee = freezed,Object? approver = freezed,Object? verifier = freezed,Object? windowStart = freezed,Object? windowEnd = freezed,Object? approvedAt = freezed,Object? approvedBy = freezed,Object? autoApproved = null,Object? implementedAt = freezed,Object? verifiedAt = freezed,Object? rejectedAt = freezed,Object? deviations = null,Object? createdAt = null,Object? updatedAt = null,Object? description = freezed,Object? implementationPlan = freezed,Object? rollbackPlan = freezed,Object? impact = freezed,Object? requirementRef = freezed,Object? ticketRef = freezed,Object? supersedesChangeId = freezed,Object? supersedesNumber = freezed,Object? supersededBy = null,Object? version = null,Object? allowedActions = null,Object? editableFields = null,Object? access = null,Object? suggestedApproverId = freezed,Object? consents = null,Object? comments = null,}) {
  return _then(_Change(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,companyId: null == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String,number: null == number ? _self.number : number // ignore: cast_nullable_to_non_nullable
as String,title: freezed == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String?,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,changeType: freezed == changeType ? _self.changeType : changeType // ignore: cast_nullable_to_non_nullable
as String?,risk: freezed == risk ? _self.risk : risk // ignore: cast_nullable_to_non_nullable
as String?,category: freezed == category ? _self.category : category // ignore: cast_nullable_to_non_nullable
as CategoryRef?,subcategory: freezed == subcategory ? _self.subcategory : subcategory // ignore: cast_nullable_to_non_nullable
as CategoryRef?,ci: null == ci ? _self._ci : ci // ignore: cast_nullable_to_non_nullable
as List<ChangeCi>,requestedBy: null == requestedBy ? _self.requestedBy : requestedBy // ignore: cast_nullable_to_non_nullable
as UserRef,assignee: freezed == assignee ? _self.assignee : assignee // ignore: cast_nullable_to_non_nullable
as UserRef?,approver: freezed == approver ? _self.approver : approver // ignore: cast_nullable_to_non_nullable
as UserRef?,verifier: freezed == verifier ? _self.verifier : verifier // ignore: cast_nullable_to_non_nullable
as UserRef?,windowStart: freezed == windowStart ? _self.windowStart : windowStart // ignore: cast_nullable_to_non_nullable
as DateTime?,windowEnd: freezed == windowEnd ? _self.windowEnd : windowEnd // ignore: cast_nullable_to_non_nullable
as DateTime?,approvedAt: freezed == approvedAt ? _self.approvedAt : approvedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,approvedBy: freezed == approvedBy ? _self.approvedBy : approvedBy // ignore: cast_nullable_to_non_nullable
as UserRef?,autoApproved: null == autoApproved ? _self.autoApproved : autoApproved // ignore: cast_nullable_to_non_nullable
as bool,implementedAt: freezed == implementedAt ? _self.implementedAt : implementedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,verifiedAt: freezed == verifiedAt ? _self.verifiedAt : verifiedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,rejectedAt: freezed == rejectedAt ? _self.rejectedAt : rejectedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,deviations: null == deviations ? _self._deviations : deviations // ignore: cast_nullable_to_non_nullable
as List<Deviation>,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,updatedAt: null == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,implementationPlan: freezed == implementationPlan ? _self.implementationPlan : implementationPlan // ignore: cast_nullable_to_non_nullable
as String?,rollbackPlan: freezed == rollbackPlan ? _self.rollbackPlan : rollbackPlan // ignore: cast_nullable_to_non_nullable
as String?,impact: freezed == impact ? _self.impact : impact // ignore: cast_nullable_to_non_nullable
as String?,requirementRef: freezed == requirementRef ? _self.requirementRef : requirementRef // ignore: cast_nullable_to_non_nullable
as String?,ticketRef: freezed == ticketRef ? _self.ticketRef : ticketRef // ignore: cast_nullable_to_non_nullable
as String?,supersedesChangeId: freezed == supersedesChangeId ? _self.supersedesChangeId : supersedesChangeId // ignore: cast_nullable_to_non_nullable
as String?,supersedesNumber: freezed == supersedesNumber ? _self.supersedesNumber : supersedesNumber // ignore: cast_nullable_to_non_nullable
as String?,supersededBy: null == supersededBy ? _self._supersededBy : supersededBy // ignore: cast_nullable_to_non_nullable
as List<LinkedChange>,version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,allowedActions: null == allowedActions ? _self._allowedActions : allowedActions // ignore: cast_nullable_to_non_nullable
as List<String>,editableFields: null == editableFields ? _self._editableFields : editableFields // ignore: cast_nullable_to_non_nullable
as List<String>,access: null == access ? _self.access : access // ignore: cast_nullable_to_non_nullable
as ChangeAccess,suggestedApproverId: freezed == suggestedApproverId ? _self.suggestedApproverId : suggestedApproverId // ignore: cast_nullable_to_non_nullable
as String?,consents: null == consents ? _self._consents : consents // ignore: cast_nullable_to_non_nullable
as List<Consent>,comments: null == comments ? _self._comments : comments // ignore: cast_nullable_to_non_nullable
as List<ChangeComment>,
  ));
}

/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$CategoryRefCopyWith<$Res>? get category {
    if (_self.category == null) {
    return null;
  }

  return $CategoryRefCopyWith<$Res>(_self.category!, (value) {
    return _then(_self.copyWith(category: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$CategoryRefCopyWith<$Res>? get subcategory {
    if (_self.subcategory == null) {
    return null;
  }

  return $CategoryRefCopyWith<$Res>(_self.subcategory!, (value) {
    return _then(_self.copyWith(subcategory: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get requestedBy {
  
  return $UserRefCopyWith<$Res>(_self.requestedBy, (value) {
    return _then(_self.copyWith(requestedBy: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get assignee {
    if (_self.assignee == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.assignee!, (value) {
    return _then(_self.copyWith(assignee: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get approver {
    if (_self.approver == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.approver!, (value) {
    return _then(_self.copyWith(approver: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get verifier {
    if (_self.verifier == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.verifier!, (value) {
    return _then(_self.copyWith(verifier: value));
  });
}/// Create a copy of Change
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res>? get approvedBy {
    if (_self.approvedBy == null) {
    return null;
  }

  return $UserRefCopyWith<$Res>(_self.approvedBy!, (value) {
    return _then(_self.copyWith(approvedBy: value));
  });
}
}


/// @nodoc
mixin _$ReadinessCheck {

 String get code; bool get ok; String get level; String get messagePl; String? get field;
/// Create a copy of ReadinessCheck
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ReadinessCheckCopyWith<ReadinessCheck> get copyWith => _$ReadinessCheckCopyWithImpl<ReadinessCheck>(this as ReadinessCheck, _$identity);

  /// Serializes this ReadinessCheck to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ReadinessCheck;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ReadinessCheck&&(identical(other.code, _this.code) || other.code == _this.code)&&(identical(other.ok, _this.ok) || other.ok == _this.ok)&&(identical(other.level, _this.level) || other.level == _this.level)&&(identical(other.messagePl, _this.messagePl) || other.messagePl == _this.messagePl)&&(identical(other.field, _this.field) || other.field == _this.field));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ReadinessCheck;
  return Object.hash(runtimeType,_this.code,_this.ok,_this.level,_this.messagePl,_this.field);
}

@override
String toString() {
  final _this = this as ReadinessCheck;
  return 'ReadinessCheck(code: ${_this.code}, ok: ${_this.ok}, level: ${_this.level}, messagePl: ${_this.messagePl}, field: ${_this.field})';
}


}

/// @nodoc
abstract mixin class $ReadinessCheckCopyWith<$Res>  {
  factory $ReadinessCheckCopyWith(ReadinessCheck value, $Res Function(ReadinessCheck) _then) = _$ReadinessCheckCopyWithImpl;
@useResult
$Res call({
 String code, bool ok, String level, String messagePl, String? field
});




}
/// @nodoc
class _$ReadinessCheckCopyWithImpl<$Res>
    implements $ReadinessCheckCopyWith<$Res> {
  _$ReadinessCheckCopyWithImpl(this._self, this._then);

  final ReadinessCheck _self;
  final $Res Function(ReadinessCheck) _then;

/// Create a copy of ReadinessCheck
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? code = null,Object? ok = null,Object? level = null,Object? messagePl = null,Object? field = freezed,}) {
  return _then(ReadinessCheck(
code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,ok: null == ok ? _self.ok : ok // ignore: cast_nullable_to_non_nullable
as bool,level: null == level ? _self.level : level // ignore: cast_nullable_to_non_nullable
as String,messagePl: null == messagePl ? _self.messagePl : messagePl // ignore: cast_nullable_to_non_nullable
as String,field: freezed == field ? _self.field : field // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [ReadinessCheck].
extension ReadinessCheckPatterns on ReadinessCheck {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ReadinessCheck value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ReadinessCheck() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ReadinessCheck value)  $default,){
final _that = this;
switch (_that) {
case _ReadinessCheck():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ReadinessCheck value)?  $default,){
final _that = this;
switch (_that) {
case _ReadinessCheck() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String code,  bool ok,  String level,  String messagePl,  String? field)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ReadinessCheck() when $default != null:
return $default(_that.code,_that.ok,_that.level,_that.messagePl,_that.field);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String code,  bool ok,  String level,  String messagePl,  String? field)  $default,) {final _that = this;
switch (_that) {
case _ReadinessCheck():
return $default(_that.code,_that.ok,_that.level,_that.messagePl,_that.field);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String code,  bool ok,  String level,  String messagePl,  String? field)?  $default,) {final _that = this;
switch (_that) {
case _ReadinessCheck() when $default != null:
return $default(_that.code,_that.ok,_that.level,_that.messagePl,_that.field);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ReadinessCheck extends ReadinessCheck {
  const _ReadinessCheck({required this.code, required this.ok, this.level = 'ok', this.messagePl = '', this.field}): super._();
  factory _ReadinessCheck.fromJson(Map<String, dynamic> json) => _$ReadinessCheckFromJson(json);

@override final  String code;
@override final  bool ok;
@override@JsonKey() final  String level;
@override@JsonKey() final  String messagePl;
@override final  String? field;

/// Create a copy of ReadinessCheck
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ReadinessCheckCopyWith<_ReadinessCheck> get copyWith => __$ReadinessCheckCopyWithImpl<_ReadinessCheck>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ReadinessCheckToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ReadinessCheck&&(identical(other.code, code) || other.code == code)&&(identical(other.ok, ok) || other.ok == ok)&&(identical(other.level, level) || other.level == level)&&(identical(other.messagePl, messagePl) || other.messagePl == messagePl)&&(identical(other.field, field) || other.field == field));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,code,ok,level,messagePl,field);
}

@override
String toString() {
    return 'ReadinessCheck(code: $code, ok: $ok, level: $level, messagePl: $messagePl, field: $field)';
}


}

/// @nodoc
abstract mixin class _$ReadinessCheckCopyWith<$Res> implements $ReadinessCheckCopyWith<$Res> {
  factory _$ReadinessCheckCopyWith(_ReadinessCheck value, $Res Function(_ReadinessCheck) _then) = __$ReadinessCheckCopyWithImpl;
@override @useResult
$Res call({
 String code, bool ok, String level, String messagePl, String? field
});




}
/// @nodoc
class __$ReadinessCheckCopyWithImpl<$Res>
    implements _$ReadinessCheckCopyWith<$Res> {
  __$ReadinessCheckCopyWithImpl(this._self, this._then);

  final _ReadinessCheck _self;
  final $Res Function(_ReadinessCheck) _then;

/// Create a copy of ReadinessCheck
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? code = null,Object? ok = null,Object? level = null,Object? messagePl = null,Object? field = freezed,}) {
  return _then(_ReadinessCheck(
code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,ok: null == ok ? _self.ok : ok // ignore: cast_nullable_to_non_nullable
as bool,level: null == level ? _self.level : level // ignore: cast_nullable_to_non_nullable
as String,messagePl: null == messagePl ? _self.messagePl : messagePl // ignore: cast_nullable_to_non_nullable
as String,field: freezed == field ? _self.field : field // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}


/// @nodoc
mixin _$Readiness {

 bool get ok; List<ReadinessCheck> get checks;
/// Create a copy of Readiness
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ReadinessCopyWith<Readiness> get copyWith => _$ReadinessCopyWithImpl<Readiness>(this as Readiness, _$identity);

  /// Serializes this Readiness to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as Readiness;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Readiness&&(identical(other.ok, _this.ok) || other.ok == _this.ok)&&const DeepCollectionEquality().equals(other.checks, _this.checks));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as Readiness;
  return Object.hash(runtimeType,_this.ok,const DeepCollectionEquality().hash(_this.checks));
}

@override
String toString() {
  final _this = this as Readiness;
  return 'Readiness(ok: ${_this.ok}, checks: ${_this.checks})';
}


}

/// @nodoc
abstract mixin class $ReadinessCopyWith<$Res>  {
  factory $ReadinessCopyWith(Readiness value, $Res Function(Readiness) _then) = _$ReadinessCopyWithImpl;
@useResult
$Res call({
 bool ok, List<ReadinessCheck> checks
});




}
/// @nodoc
class _$ReadinessCopyWithImpl<$Res>
    implements $ReadinessCopyWith<$Res> {
  _$ReadinessCopyWithImpl(this._self, this._then);

  final Readiness _self;
  final $Res Function(Readiness) _then;

/// Create a copy of Readiness
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? ok = null,Object? checks = null,}) {
  return _then(Readiness(
ok: null == ok ? _self.ok : ok // ignore: cast_nullable_to_non_nullable
as bool,checks: null == checks ? _self.checks : checks // ignore: cast_nullable_to_non_nullable
as List<ReadinessCheck>,
  ));
}

}


/// Adds pattern-matching-related methods to [Readiness].
extension ReadinessPatterns on Readiness {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Readiness value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Readiness() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Readiness value)  $default,){
final _that = this;
switch (_that) {
case _Readiness():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Readiness value)?  $default,){
final _that = this;
switch (_that) {
case _Readiness() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( bool ok,  List<ReadinessCheck> checks)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Readiness() when $default != null:
return $default(_that.ok,_that.checks);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( bool ok,  List<ReadinessCheck> checks)  $default,) {final _that = this;
switch (_that) {
case _Readiness():
return $default(_that.ok,_that.checks);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( bool ok,  List<ReadinessCheck> checks)?  $default,) {final _that = this;
switch (_that) {
case _Readiness() when $default != null:
return $default(_that.ok,_that.checks);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Readiness implements Readiness {
  const _Readiness({required this.ok,  List<ReadinessCheck> checks = const <ReadinessCheck>[]}): _checks = checks;
  factory _Readiness.fromJson(Map<String, dynamic> json) => _$ReadinessFromJson(json);

@override final  bool ok;
 final  List<ReadinessCheck> _checks;
@override@JsonKey() List<ReadinessCheck> get checks {
  if (_checks is EqualUnmodifiableListView) return _checks;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_checks);
}


/// Create a copy of Readiness
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ReadinessCopyWith<_Readiness> get copyWith => __$ReadinessCopyWithImpl<_Readiness>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ReadinessToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _Readiness&&(identical(other.ok, ok) || other.ok == ok)&&const DeepCollectionEquality().equals(other.checks, _checks));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,ok,const DeepCollectionEquality().hash(_checks));
}

@override
String toString() {
    return 'Readiness(ok: $ok, checks: $checks)';
}


}

/// @nodoc
abstract mixin class _$ReadinessCopyWith<$Res> implements $ReadinessCopyWith<$Res> {
  factory _$ReadinessCopyWith(_Readiness value, $Res Function(_Readiness) _then) = __$ReadinessCopyWithImpl;
@override @useResult
$Res call({
 bool ok, List<ReadinessCheck> checks
});




}
/// @nodoc
class __$ReadinessCopyWithImpl<$Res>
    implements _$ReadinessCopyWith<$Res> {
  __$ReadinessCopyWithImpl(this._self, this._then);

  final _Readiness _self;
  final $Res Function(_Readiness) _then;

/// Create a copy of Readiness
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? ok = null,Object? checks = null,}) {
  return _then(_Readiness(
ok: null == ok ? _self.ok : ok // ignore: cast_nullable_to_non_nullable
as bool,checks: null == checks ? _self._checks : checks // ignore: cast_nullable_to_non_nullable
as List<ReadinessCheck>,
  ));
}


}


/// @nodoc
mixin _$ActionResult {

 String get action; String get fromStatus; String get toStatus; bool get performedBySystem; List<Map<String, dynamic>> get warnings; Change get change;
/// Create a copy of ActionResult
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ActionResultCopyWith<ActionResult> get copyWith => _$ActionResultCopyWithImpl<ActionResult>(this as ActionResult, _$identity);

  /// Serializes this ActionResult to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ActionResult;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ActionResult&&(identical(other.action, _this.action) || other.action == _this.action)&&(identical(other.fromStatus, _this.fromStatus) || other.fromStatus == _this.fromStatus)&&(identical(other.toStatus, _this.toStatus) || other.toStatus == _this.toStatus)&&(identical(other.performedBySystem, _this.performedBySystem) || other.performedBySystem == _this.performedBySystem)&&const DeepCollectionEquality().equals(other.warnings, _this.warnings)&&(identical(other.change, _this.change) || other.change == _this.change));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ActionResult;
  return Object.hash(runtimeType,_this.action,_this.fromStatus,_this.toStatus,_this.performedBySystem,const DeepCollectionEquality().hash(_this.warnings),_this.change);
}

@override
String toString() {
  final _this = this as ActionResult;
  return 'ActionResult(action: ${_this.action}, fromStatus: ${_this.fromStatus}, toStatus: ${_this.toStatus}, performedBySystem: ${_this.performedBySystem}, warnings: ${_this.warnings}, change: ${_this.change})';
}


}

/// @nodoc
abstract mixin class $ActionResultCopyWith<$Res>  {
  factory $ActionResultCopyWith(ActionResult value, $Res Function(ActionResult) _then) = _$ActionResultCopyWithImpl;
@useResult
$Res call({
 String action, String fromStatus, String toStatus, bool performedBySystem, List<Map<String, dynamic>> warnings, Change change
});


$ChangeCopyWith<$Res> get change;

}
/// @nodoc
class _$ActionResultCopyWithImpl<$Res>
    implements $ActionResultCopyWith<$Res> {
  _$ActionResultCopyWithImpl(this._self, this._then);

  final ActionResult _self;
  final $Res Function(ActionResult) _then;

/// Create a copy of ActionResult
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? action = null,Object? fromStatus = null,Object? toStatus = null,Object? performedBySystem = null,Object? warnings = null,Object? change = null,}) {
  return _then(ActionResult(
action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,fromStatus: null == fromStatus ? _self.fromStatus : fromStatus // ignore: cast_nullable_to_non_nullable
as String,toStatus: null == toStatus ? _self.toStatus : toStatus // ignore: cast_nullable_to_non_nullable
as String,performedBySystem: null == performedBySystem ? _self.performedBySystem : performedBySystem // ignore: cast_nullable_to_non_nullable
as bool,warnings: null == warnings ? _self.warnings : warnings // ignore: cast_nullable_to_non_nullable
as List<Map<String, dynamic>>,change: null == change ? _self.change : change // ignore: cast_nullable_to_non_nullable
as Change,
  ));
}
/// Create a copy of ActionResult
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$ChangeCopyWith<$Res> get change {
  
  return $ChangeCopyWith<$Res>(_self.change, (value) {
    return _then(_self.copyWith(change: value));
  });
}
}


/// Adds pattern-matching-related methods to [ActionResult].
extension ActionResultPatterns on ActionResult {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ActionResult value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ActionResult() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ActionResult value)  $default,){
final _that = this;
switch (_that) {
case _ActionResult():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ActionResult value)?  $default,){
final _that = this;
switch (_that) {
case _ActionResult() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String action,  String fromStatus,  String toStatus,  bool performedBySystem,  List<Map<String, dynamic>> warnings,  Change change)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ActionResult() when $default != null:
return $default(_that.action,_that.fromStatus,_that.toStatus,_that.performedBySystem,_that.warnings,_that.change);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String action,  String fromStatus,  String toStatus,  bool performedBySystem,  List<Map<String, dynamic>> warnings,  Change change)  $default,) {final _that = this;
switch (_that) {
case _ActionResult():
return $default(_that.action,_that.fromStatus,_that.toStatus,_that.performedBySystem,_that.warnings,_that.change);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String action,  String fromStatus,  String toStatus,  bool performedBySystem,  List<Map<String, dynamic>> warnings,  Change change)?  $default,) {final _that = this;
switch (_that) {
case _ActionResult() when $default != null:
return $default(_that.action,_that.fromStatus,_that.toStatus,_that.performedBySystem,_that.warnings,_that.change);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ActionResult implements ActionResult {
  const _ActionResult({required this.action, required this.fromStatus, required this.toStatus, this.performedBySystem = false,  List<Map<String, dynamic>> warnings = const <Map<String, dynamic>>[], required this.change}): _warnings = warnings;
  factory _ActionResult.fromJson(Map<String, dynamic> json) => _$ActionResultFromJson(json);

@override final  String action;
@override final  String fromStatus;
@override final  String toStatus;
@override@JsonKey() final  bool performedBySystem;
 final  List<Map<String, dynamic>> _warnings;
@override@JsonKey() List<Map<String, dynamic>> get warnings {
  if (_warnings is EqualUnmodifiableListView) return _warnings;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_warnings);
}

@override final  Change change;

/// Create a copy of ActionResult
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ActionResultCopyWith<_ActionResult> get copyWith => __$ActionResultCopyWithImpl<_ActionResult>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ActionResultToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ActionResult&&(identical(other.action, action) || other.action == action)&&(identical(other.fromStatus, fromStatus) || other.fromStatus == fromStatus)&&(identical(other.toStatus, toStatus) || other.toStatus == toStatus)&&(identical(other.performedBySystem, performedBySystem) || other.performedBySystem == performedBySystem)&&const DeepCollectionEquality().equals(other.warnings, _warnings)&&(identical(other.change, change) || other.change == change));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,action,fromStatus,toStatus,performedBySystem,const DeepCollectionEquality().hash(_warnings),change);
}

@override
String toString() {
    return 'ActionResult(action: $action, fromStatus: $fromStatus, toStatus: $toStatus, performedBySystem: $performedBySystem, warnings: $warnings, change: $change)';
}


}

/// @nodoc
abstract mixin class _$ActionResultCopyWith<$Res> implements $ActionResultCopyWith<$Res> {
  factory _$ActionResultCopyWith(_ActionResult value, $Res Function(_ActionResult) _then) = __$ActionResultCopyWithImpl;
@override @useResult
$Res call({
 String action, String fromStatus, String toStatus, bool performedBySystem, List<Map<String, dynamic>> warnings, Change change
});


@override $ChangeCopyWith<$Res> get change;

}
/// @nodoc
class __$ActionResultCopyWithImpl<$Res>
    implements _$ActionResultCopyWith<$Res> {
  __$ActionResultCopyWithImpl(this._self, this._then);

  final _ActionResult _self;
  final $Res Function(_ActionResult) _then;

/// Create a copy of ActionResult
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? action = null,Object? fromStatus = null,Object? toStatus = null,Object? performedBySystem = null,Object? warnings = null,Object? change = null,}) {
  return _then(_ActionResult(
action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,fromStatus: null == fromStatus ? _self.fromStatus : fromStatus // ignore: cast_nullable_to_non_nullable
as String,toStatus: null == toStatus ? _self.toStatus : toStatus // ignore: cast_nullable_to_non_nullable
as String,performedBySystem: null == performedBySystem ? _self.performedBySystem : performedBySystem // ignore: cast_nullable_to_non_nullable
as bool,warnings: null == warnings ? _self._warnings : warnings // ignore: cast_nullable_to_non_nullable
as List<Map<String, dynamic>>,change: null == change ? _self.change : change // ignore: cast_nullable_to_non_nullable
as Change,
  ));
}

/// Create a copy of ActionResult
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$ChangeCopyWith<$Res> get change {
  
  return $ChangeCopyWith<$Res>(_self.change, (value) {
    return _then(_self.copyWith(change: value));
  });
}
}


/// @nodoc
mixin _$Attachment {

 String get id; String get changeId; String get filename; String get contentType; int get size; String get sha256; UserRef get uploadedBy; DateTime get createdAt;
/// Create a copy of Attachment
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AttachmentCopyWith<Attachment> get copyWith => _$AttachmentCopyWithImpl<Attachment>(this as Attachment, _$identity);

  /// Serializes this Attachment to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as Attachment;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Attachment&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.changeId, _this.changeId) || other.changeId == _this.changeId)&&(identical(other.filename, _this.filename) || other.filename == _this.filename)&&(identical(other.contentType, _this.contentType) || other.contentType == _this.contentType)&&(identical(other.size, _this.size) || other.size == _this.size)&&(identical(other.sha256, _this.sha256) || other.sha256 == _this.sha256)&&(identical(other.uploadedBy, _this.uploadedBy) || other.uploadedBy == _this.uploadedBy)&&(identical(other.createdAt, _this.createdAt) || other.createdAt == _this.createdAt));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as Attachment;
  return Object.hash(runtimeType,_this.id,_this.changeId,_this.filename,_this.contentType,_this.size,_this.sha256,_this.uploadedBy,_this.createdAt);
}

@override
String toString() {
  final _this = this as Attachment;
  return 'Attachment(id: ${_this.id}, changeId: ${_this.changeId}, filename: ${_this.filename}, contentType: ${_this.contentType}, size: ${_this.size}, sha256: ${_this.sha256}, uploadedBy: ${_this.uploadedBy}, createdAt: ${_this.createdAt})';
}


}

/// @nodoc
abstract mixin class $AttachmentCopyWith<$Res>  {
  factory $AttachmentCopyWith(Attachment value, $Res Function(Attachment) _then) = _$AttachmentCopyWithImpl;
@useResult
$Res call({
 String id, String changeId, String filename, String contentType, int size, String sha256, UserRef uploadedBy, DateTime createdAt
});


$UserRefCopyWith<$Res> get uploadedBy;

}
/// @nodoc
class _$AttachmentCopyWithImpl<$Res>
    implements $AttachmentCopyWith<$Res> {
  _$AttachmentCopyWithImpl(this._self, this._then);

  final Attachment _self;
  final $Res Function(Attachment) _then;

/// Create a copy of Attachment
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? changeId = null,Object? filename = null,Object? contentType = null,Object? size = null,Object? sha256 = null,Object? uploadedBy = null,Object? createdAt = null,}) {
  return _then(Attachment(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,changeId: null == changeId ? _self.changeId : changeId // ignore: cast_nullable_to_non_nullable
as String,filename: null == filename ? _self.filename : filename // ignore: cast_nullable_to_non_nullable
as String,contentType: null == contentType ? _self.contentType : contentType // ignore: cast_nullable_to_non_nullable
as String,size: null == size ? _self.size : size // ignore: cast_nullable_to_non_nullable
as int,sha256: null == sha256 ? _self.sha256 : sha256 // ignore: cast_nullable_to_non_nullable
as String,uploadedBy: null == uploadedBy ? _self.uploadedBy : uploadedBy // ignore: cast_nullable_to_non_nullable
as UserRef,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,
  ));
}
/// Create a copy of Attachment
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get uploadedBy {
  
  return $UserRefCopyWith<$Res>(_self.uploadedBy, (value) {
    return _then(_self.copyWith(uploadedBy: value));
  });
}
}


/// Adds pattern-matching-related methods to [Attachment].
extension AttachmentPatterns on Attachment {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Attachment value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Attachment() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Attachment value)  $default,){
final _that = this;
switch (_that) {
case _Attachment():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Attachment value)?  $default,){
final _that = this;
switch (_that) {
case _Attachment() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String changeId,  String filename,  String contentType,  int size,  String sha256,  UserRef uploadedBy,  DateTime createdAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Attachment() when $default != null:
return $default(_that.id,_that.changeId,_that.filename,_that.contentType,_that.size,_that.sha256,_that.uploadedBy,_that.createdAt);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String changeId,  String filename,  String contentType,  int size,  String sha256,  UserRef uploadedBy,  DateTime createdAt)  $default,) {final _that = this;
switch (_that) {
case _Attachment():
return $default(_that.id,_that.changeId,_that.filename,_that.contentType,_that.size,_that.sha256,_that.uploadedBy,_that.createdAt);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String changeId,  String filename,  String contentType,  int size,  String sha256,  UserRef uploadedBy,  DateTime createdAt)?  $default,) {final _that = this;
switch (_that) {
case _Attachment() when $default != null:
return $default(_that.id,_that.changeId,_that.filename,_that.contentType,_that.size,_that.sha256,_that.uploadedBy,_that.createdAt);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Attachment implements Attachment {
  const _Attachment({required this.id, required this.changeId, required this.filename, this.contentType = 'application/octet-stream', required this.size, required this.sha256, required this.uploadedBy, required this.createdAt});
  factory _Attachment.fromJson(Map<String, dynamic> json) => _$AttachmentFromJson(json);

@override final  String id;
@override final  String changeId;
@override final  String filename;
@override@JsonKey() final  String contentType;
@override final  int size;
@override final  String sha256;
@override final  UserRef uploadedBy;
@override final  DateTime createdAt;

/// Create a copy of Attachment
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AttachmentCopyWith<_Attachment> get copyWith => __$AttachmentCopyWithImpl<_Attachment>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$AttachmentToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _Attachment&&(identical(other.id, id) || other.id == id)&&(identical(other.changeId, changeId) || other.changeId == changeId)&&(identical(other.filename, filename) || other.filename == filename)&&(identical(other.contentType, contentType) || other.contentType == contentType)&&(identical(other.size, size) || other.size == size)&&(identical(other.sha256, sha256) || other.sha256 == sha256)&&(identical(other.uploadedBy, uploadedBy) || other.uploadedBy == uploadedBy)&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,changeId,filename,contentType,size,sha256,uploadedBy,createdAt);
}

@override
String toString() {
    return 'Attachment(id: $id, changeId: $changeId, filename: $filename, contentType: $contentType, size: $size, sha256: $sha256, uploadedBy: $uploadedBy, createdAt: $createdAt)';
}


}

/// @nodoc
abstract mixin class _$AttachmentCopyWith<$Res> implements $AttachmentCopyWith<$Res> {
  factory _$AttachmentCopyWith(_Attachment value, $Res Function(_Attachment) _then) = __$AttachmentCopyWithImpl;
@override @useResult
$Res call({
 String id, String changeId, String filename, String contentType, int size, String sha256, UserRef uploadedBy, DateTime createdAt
});


@override $UserRefCopyWith<$Res> get uploadedBy;

}
/// @nodoc
class __$AttachmentCopyWithImpl<$Res>
    implements _$AttachmentCopyWith<$Res> {
  __$AttachmentCopyWithImpl(this._self, this._then);

  final _Attachment _self;
  final $Res Function(_Attachment) _then;

/// Create a copy of Attachment
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? changeId = null,Object? filename = null,Object? contentType = null,Object? size = null,Object? sha256 = null,Object? uploadedBy = null,Object? createdAt = null,}) {
  return _then(_Attachment(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,changeId: null == changeId ? _self.changeId : changeId // ignore: cast_nullable_to_non_nullable
as String,filename: null == filename ? _self.filename : filename // ignore: cast_nullable_to_non_nullable
as String,contentType: null == contentType ? _self.contentType : contentType // ignore: cast_nullable_to_non_nullable
as String,size: null == size ? _self.size : size // ignore: cast_nullable_to_non_nullable
as int,sha256: null == sha256 ? _self.sha256 : sha256 // ignore: cast_nullable_to_non_nullable
as String,uploadedBy: null == uploadedBy ? _self.uploadedBy : uploadedBy // ignore: cast_nullable_to_non_nullable
as UserRef,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,
  ));
}

/// Create a copy of Attachment
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get uploadedBy {
  
  return $UserRefCopyWith<$Res>(_self.uploadedBy, (value) {
    return _then(_self.copyWith(uploadedBy: value));
  });
}
}


/// @nodoc
mixin _$ChangeStats {

 int get pendingApproval; int get approvedNotImplemented;@JsonKey(name: 'emergency_last_30_days') int get emergencyLast30Days; int get implementedNotVerified;@JsonKey(name: 'emergency_not_approved_in_24h') int get emergencyNotApprovedIn24h; int get implementedOutsideWindow; Map<String, int> get byStatus;
/// Create a copy of ChangeStats
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ChangeStatsCopyWith<ChangeStats> get copyWith => _$ChangeStatsCopyWithImpl<ChangeStats>(this as ChangeStats, _$identity);

  /// Serializes this ChangeStats to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ChangeStats;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ChangeStats&&(identical(other.pendingApproval, _this.pendingApproval) || other.pendingApproval == _this.pendingApproval)&&(identical(other.approvedNotImplemented, _this.approvedNotImplemented) || other.approvedNotImplemented == _this.approvedNotImplemented)&&(identical(other.emergencyLast30Days, _this.emergencyLast30Days) || other.emergencyLast30Days == _this.emergencyLast30Days)&&(identical(other.implementedNotVerified, _this.implementedNotVerified) || other.implementedNotVerified == _this.implementedNotVerified)&&(identical(other.emergencyNotApprovedIn24h, _this.emergencyNotApprovedIn24h) || other.emergencyNotApprovedIn24h == _this.emergencyNotApprovedIn24h)&&(identical(other.implementedOutsideWindow, _this.implementedOutsideWindow) || other.implementedOutsideWindow == _this.implementedOutsideWindow)&&const DeepCollectionEquality().equals(other.byStatus, _this.byStatus));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ChangeStats;
  return Object.hash(runtimeType,_this.pendingApproval,_this.approvedNotImplemented,_this.emergencyLast30Days,_this.implementedNotVerified,_this.emergencyNotApprovedIn24h,_this.implementedOutsideWindow,const DeepCollectionEquality().hash(_this.byStatus));
}

@override
String toString() {
  final _this = this as ChangeStats;
  return 'ChangeStats(pendingApproval: ${_this.pendingApproval}, approvedNotImplemented: ${_this.approvedNotImplemented}, emergencyLast30Days: ${_this.emergencyLast30Days}, implementedNotVerified: ${_this.implementedNotVerified}, emergencyNotApprovedIn24h: ${_this.emergencyNotApprovedIn24h}, implementedOutsideWindow: ${_this.implementedOutsideWindow}, byStatus: ${_this.byStatus})';
}


}

/// @nodoc
abstract mixin class $ChangeStatsCopyWith<$Res>  {
  factory $ChangeStatsCopyWith(ChangeStats value, $Res Function(ChangeStats) _then) = _$ChangeStatsCopyWithImpl;
@useResult
$Res call({
 int pendingApproval, int approvedNotImplemented,@JsonKey(name: 'emergency_last_30_days') int emergencyLast30Days, int implementedNotVerified,@JsonKey(name: 'emergency_not_approved_in_24h') int emergencyNotApprovedIn24h, int implementedOutsideWindow, Map<String, int> byStatus
});




}
/// @nodoc
class _$ChangeStatsCopyWithImpl<$Res>
    implements $ChangeStatsCopyWith<$Res> {
  _$ChangeStatsCopyWithImpl(this._self, this._then);

  final ChangeStats _self;
  final $Res Function(ChangeStats) _then;

/// Create a copy of ChangeStats
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? pendingApproval = null,Object? approvedNotImplemented = null,Object? emergencyLast30Days = null,Object? implementedNotVerified = null,Object? emergencyNotApprovedIn24h = null,Object? implementedOutsideWindow = null,Object? byStatus = null,}) {
  return _then(ChangeStats(
pendingApproval: null == pendingApproval ? _self.pendingApproval : pendingApproval // ignore: cast_nullable_to_non_nullable
as int,approvedNotImplemented: null == approvedNotImplemented ? _self.approvedNotImplemented : approvedNotImplemented // ignore: cast_nullable_to_non_nullable
as int,emergencyLast30Days: null == emergencyLast30Days ? _self.emergencyLast30Days : emergencyLast30Days // ignore: cast_nullable_to_non_nullable
as int,implementedNotVerified: null == implementedNotVerified ? _self.implementedNotVerified : implementedNotVerified // ignore: cast_nullable_to_non_nullable
as int,emergencyNotApprovedIn24h: null == emergencyNotApprovedIn24h ? _self.emergencyNotApprovedIn24h : emergencyNotApprovedIn24h // ignore: cast_nullable_to_non_nullable
as int,implementedOutsideWindow: null == implementedOutsideWindow ? _self.implementedOutsideWindow : implementedOutsideWindow // ignore: cast_nullable_to_non_nullable
as int,byStatus: null == byStatus ? _self.byStatus : byStatus // ignore: cast_nullable_to_non_nullable
as Map<String, int>,
  ));
}

}


/// Adds pattern-matching-related methods to [ChangeStats].
extension ChangeStatsPatterns on ChangeStats {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ChangeStats value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ChangeStats() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ChangeStats value)  $default,){
final _that = this;
switch (_that) {
case _ChangeStats():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ChangeStats value)?  $default,){
final _that = this;
switch (_that) {
case _ChangeStats() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( int pendingApproval,  int approvedNotImplemented, @JsonKey(name: 'emergency_last_30_days')  int emergencyLast30Days,  int implementedNotVerified, @JsonKey(name: 'emergency_not_approved_in_24h')  int emergencyNotApprovedIn24h,  int implementedOutsideWindow,  Map<String, int> byStatus)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ChangeStats() when $default != null:
return $default(_that.pendingApproval,_that.approvedNotImplemented,_that.emergencyLast30Days,_that.implementedNotVerified,_that.emergencyNotApprovedIn24h,_that.implementedOutsideWindow,_that.byStatus);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( int pendingApproval,  int approvedNotImplemented, @JsonKey(name: 'emergency_last_30_days')  int emergencyLast30Days,  int implementedNotVerified, @JsonKey(name: 'emergency_not_approved_in_24h')  int emergencyNotApprovedIn24h,  int implementedOutsideWindow,  Map<String, int> byStatus)  $default,) {final _that = this;
switch (_that) {
case _ChangeStats():
return $default(_that.pendingApproval,_that.approvedNotImplemented,_that.emergencyLast30Days,_that.implementedNotVerified,_that.emergencyNotApprovedIn24h,_that.implementedOutsideWindow,_that.byStatus);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( int pendingApproval,  int approvedNotImplemented, @JsonKey(name: 'emergency_last_30_days')  int emergencyLast30Days,  int implementedNotVerified, @JsonKey(name: 'emergency_not_approved_in_24h')  int emergencyNotApprovedIn24h,  int implementedOutsideWindow,  Map<String, int> byStatus)?  $default,) {final _that = this;
switch (_that) {
case _ChangeStats() when $default != null:
return $default(_that.pendingApproval,_that.approvedNotImplemented,_that.emergencyLast30Days,_that.implementedNotVerified,_that.emergencyNotApprovedIn24h,_that.implementedOutsideWindow,_that.byStatus);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ChangeStats implements ChangeStats {
  const _ChangeStats({this.pendingApproval = 0, this.approvedNotImplemented = 0, @JsonKey(name: 'emergency_last_30_days') this.emergencyLast30Days = 0, this.implementedNotVerified = 0, @JsonKey(name: 'emergency_not_approved_in_24h') this.emergencyNotApprovedIn24h = 0, this.implementedOutsideWindow = 0,  Map<String, int> byStatus = const <String, int>{}}): _byStatus = byStatus;
  factory _ChangeStats.fromJson(Map<String, dynamic> json) => _$ChangeStatsFromJson(json);

@override@JsonKey() final  int pendingApproval;
@override@JsonKey() final  int approvedNotImplemented;
@override@JsonKey(name: 'emergency_last_30_days') final  int emergencyLast30Days;
@override@JsonKey() final  int implementedNotVerified;
@override@JsonKey(name: 'emergency_not_approved_in_24h') final  int emergencyNotApprovedIn24h;
@override@JsonKey() final  int implementedOutsideWindow;
 final  Map<String, int> _byStatus;
@override@JsonKey() Map<String, int> get byStatus {
  if (_byStatus is EqualUnmodifiableMapView) return _byStatus;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_byStatus);
}


/// Create a copy of ChangeStats
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ChangeStatsCopyWith<_ChangeStats> get copyWith => __$ChangeStatsCopyWithImpl<_ChangeStats>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ChangeStatsToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ChangeStats&&(identical(other.pendingApproval, pendingApproval) || other.pendingApproval == pendingApproval)&&(identical(other.approvedNotImplemented, approvedNotImplemented) || other.approvedNotImplemented == approvedNotImplemented)&&(identical(other.emergencyLast30Days, emergencyLast30Days) || other.emergencyLast30Days == emergencyLast30Days)&&(identical(other.implementedNotVerified, implementedNotVerified) || other.implementedNotVerified == implementedNotVerified)&&(identical(other.emergencyNotApprovedIn24h, emergencyNotApprovedIn24h) || other.emergencyNotApprovedIn24h == emergencyNotApprovedIn24h)&&(identical(other.implementedOutsideWindow, implementedOutsideWindow) || other.implementedOutsideWindow == implementedOutsideWindow)&&const DeepCollectionEquality().equals(other.byStatus, _byStatus));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,pendingApproval,approvedNotImplemented,emergencyLast30Days,implementedNotVerified,emergencyNotApprovedIn24h,implementedOutsideWindow,const DeepCollectionEquality().hash(_byStatus));
}

@override
String toString() {
    return 'ChangeStats(pendingApproval: $pendingApproval, approvedNotImplemented: $approvedNotImplemented, emergencyLast30Days: $emergencyLast30Days, implementedNotVerified: $implementedNotVerified, emergencyNotApprovedIn24h: $emergencyNotApprovedIn24h, implementedOutsideWindow: $implementedOutsideWindow, byStatus: $byStatus)';
}


}

/// @nodoc
abstract mixin class _$ChangeStatsCopyWith<$Res> implements $ChangeStatsCopyWith<$Res> {
  factory _$ChangeStatsCopyWith(_ChangeStats value, $Res Function(_ChangeStats) _then) = __$ChangeStatsCopyWithImpl;
@override @useResult
$Res call({
 int pendingApproval, int approvedNotImplemented,@JsonKey(name: 'emergency_last_30_days') int emergencyLast30Days, int implementedNotVerified,@JsonKey(name: 'emergency_not_approved_in_24h') int emergencyNotApprovedIn24h, int implementedOutsideWindow, Map<String, int> byStatus
});




}
/// @nodoc
class __$ChangeStatsCopyWithImpl<$Res>
    implements _$ChangeStatsCopyWith<$Res> {
  __$ChangeStatsCopyWithImpl(this._self, this._then);

  final _ChangeStats _self;
  final $Res Function(_ChangeStats) _then;

/// Create a copy of ChangeStats
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? pendingApproval = null,Object? approvedNotImplemented = null,Object? emergencyLast30Days = null,Object? implementedNotVerified = null,Object? emergencyNotApprovedIn24h = null,Object? implementedOutsideWindow = null,Object? byStatus = null,}) {
  return _then(_ChangeStats(
pendingApproval: null == pendingApproval ? _self.pendingApproval : pendingApproval // ignore: cast_nullable_to_non_nullable
as int,approvedNotImplemented: null == approvedNotImplemented ? _self.approvedNotImplemented : approvedNotImplemented // ignore: cast_nullable_to_non_nullable
as int,emergencyLast30Days: null == emergencyLast30Days ? _self.emergencyLast30Days : emergencyLast30Days // ignore: cast_nullable_to_non_nullable
as int,implementedNotVerified: null == implementedNotVerified ? _self.implementedNotVerified : implementedNotVerified // ignore: cast_nullable_to_non_nullable
as int,emergencyNotApprovedIn24h: null == emergencyNotApprovedIn24h ? _self.emergencyNotApprovedIn24h : emergencyNotApprovedIn24h // ignore: cast_nullable_to_non_nullable
as int,implementedOutsideWindow: null == implementedOutsideWindow ? _self.implementedOutsideWindow : implementedOutsideWindow // ignore: cast_nullable_to_non_nullable
as int,byStatus: null == byStatus ? _self._byStatus : byStatus // ignore: cast_nullable_to_non_nullable
as Map<String, int>,
  ));
}


}


/// @nodoc
mixin _$AuditEntry {

 int get seq; DateTime get occurredAt; String? get actorId; String get actorDisplay; List<String> get actorRoles; String? get ipAddress; String get requestId; String get entityType; String? get entityId; String get action; Map<String, dynamic> get diff; Map<String, dynamic> get context; String get prevHash; String get hash; bool get hashValid;
/// Create a copy of AuditEntry
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AuditEntryCopyWith<AuditEntry> get copyWith => _$AuditEntryCopyWithImpl<AuditEntry>(this as AuditEntry, _$identity);

  /// Serializes this AuditEntry to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as AuditEntry;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AuditEntry&&(identical(other.seq, _this.seq) || other.seq == _this.seq)&&(identical(other.occurredAt, _this.occurredAt) || other.occurredAt == _this.occurredAt)&&(identical(other.actorId, _this.actorId) || other.actorId == _this.actorId)&&(identical(other.actorDisplay, _this.actorDisplay) || other.actorDisplay == _this.actorDisplay)&&const DeepCollectionEquality().equals(other.actorRoles, _this.actorRoles)&&(identical(other.ipAddress, _this.ipAddress) || other.ipAddress == _this.ipAddress)&&(identical(other.requestId, _this.requestId) || other.requestId == _this.requestId)&&(identical(other.entityType, _this.entityType) || other.entityType == _this.entityType)&&(identical(other.entityId, _this.entityId) || other.entityId == _this.entityId)&&(identical(other.action, _this.action) || other.action == _this.action)&&const DeepCollectionEquality().equals(other.diff, _this.diff)&&const DeepCollectionEquality().equals(other.context, _this.context)&&(identical(other.prevHash, _this.prevHash) || other.prevHash == _this.prevHash)&&(identical(other.hash, _this.hash) || other.hash == _this.hash)&&(identical(other.hashValid, _this.hashValid) || other.hashValid == _this.hashValid));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as AuditEntry;
  return Object.hash(runtimeType,_this.seq,_this.occurredAt,_this.actorId,_this.actorDisplay,const DeepCollectionEquality().hash(_this.actorRoles),_this.ipAddress,_this.requestId,_this.entityType,_this.entityId,_this.action,const DeepCollectionEquality().hash(_this.diff),const DeepCollectionEquality().hash(_this.context),_this.prevHash,_this.hash,_this.hashValid);
}

@override
String toString() {
  final _this = this as AuditEntry;
  return 'AuditEntry(seq: ${_this.seq}, occurredAt: ${_this.occurredAt}, actorId: ${_this.actorId}, actorDisplay: ${_this.actorDisplay}, actorRoles: ${_this.actorRoles}, ipAddress: ${_this.ipAddress}, requestId: ${_this.requestId}, entityType: ${_this.entityType}, entityId: ${_this.entityId}, action: ${_this.action}, diff: ${_this.diff}, context: ${_this.context}, prevHash: ${_this.prevHash}, hash: ${_this.hash}, hashValid: ${_this.hashValid})';
}


}

/// @nodoc
abstract mixin class $AuditEntryCopyWith<$Res>  {
  factory $AuditEntryCopyWith(AuditEntry value, $Res Function(AuditEntry) _then) = _$AuditEntryCopyWithImpl;
@useResult
$Res call({
 int seq, DateTime occurredAt, String? actorId, String actorDisplay, List<String> actorRoles, String? ipAddress, String requestId, String entityType, String? entityId, String action, Map<String, dynamic> diff, Map<String, dynamic> context, String prevHash, String hash, bool hashValid
});




}
/// @nodoc
class _$AuditEntryCopyWithImpl<$Res>
    implements $AuditEntryCopyWith<$Res> {
  _$AuditEntryCopyWithImpl(this._self, this._then);

  final AuditEntry _self;
  final $Res Function(AuditEntry) _then;

/// Create a copy of AuditEntry
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? seq = null,Object? occurredAt = null,Object? actorId = freezed,Object? actorDisplay = null,Object? actorRoles = null,Object? ipAddress = freezed,Object? requestId = null,Object? entityType = null,Object? entityId = freezed,Object? action = null,Object? diff = null,Object? context = null,Object? prevHash = null,Object? hash = null,Object? hashValid = null,}) {
  return _then(AuditEntry(
seq: null == seq ? _self.seq : seq // ignore: cast_nullable_to_non_nullable
as int,occurredAt: null == occurredAt ? _self.occurredAt : occurredAt // ignore: cast_nullable_to_non_nullable
as DateTime,actorId: freezed == actorId ? _self.actorId : actorId // ignore: cast_nullable_to_non_nullable
as String?,actorDisplay: null == actorDisplay ? _self.actorDisplay : actorDisplay // ignore: cast_nullable_to_non_nullable
as String,actorRoles: null == actorRoles ? _self.actorRoles : actorRoles // ignore: cast_nullable_to_non_nullable
as List<String>,ipAddress: freezed == ipAddress ? _self.ipAddress : ipAddress // ignore: cast_nullable_to_non_nullable
as String?,requestId: null == requestId ? _self.requestId : requestId // ignore: cast_nullable_to_non_nullable
as String,entityType: null == entityType ? _self.entityType : entityType // ignore: cast_nullable_to_non_nullable
as String,entityId: freezed == entityId ? _self.entityId : entityId // ignore: cast_nullable_to_non_nullable
as String?,action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,diff: null == diff ? _self.diff : diff // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,context: null == context ? _self.context : context // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,prevHash: null == prevHash ? _self.prevHash : prevHash // ignore: cast_nullable_to_non_nullable
as String,hash: null == hash ? _self.hash : hash // ignore: cast_nullable_to_non_nullable
as String,hashValid: null == hashValid ? _self.hashValid : hashValid // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [AuditEntry].
extension AuditEntryPatterns on AuditEntry {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AuditEntry value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AuditEntry() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AuditEntry value)  $default,){
final _that = this;
switch (_that) {
case _AuditEntry():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AuditEntry value)?  $default,){
final _that = this;
switch (_that) {
case _AuditEntry() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( int seq,  DateTime occurredAt,  String? actorId,  String actorDisplay,  List<String> actorRoles,  String? ipAddress,  String requestId,  String entityType,  String? entityId,  String action,  Map<String, dynamic> diff,  Map<String, dynamic> context,  String prevHash,  String hash,  bool hashValid)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AuditEntry() when $default != null:
return $default(_that.seq,_that.occurredAt,_that.actorId,_that.actorDisplay,_that.actorRoles,_that.ipAddress,_that.requestId,_that.entityType,_that.entityId,_that.action,_that.diff,_that.context,_that.prevHash,_that.hash,_that.hashValid);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( int seq,  DateTime occurredAt,  String? actorId,  String actorDisplay,  List<String> actorRoles,  String? ipAddress,  String requestId,  String entityType,  String? entityId,  String action,  Map<String, dynamic> diff,  Map<String, dynamic> context,  String prevHash,  String hash,  bool hashValid)  $default,) {final _that = this;
switch (_that) {
case _AuditEntry():
return $default(_that.seq,_that.occurredAt,_that.actorId,_that.actorDisplay,_that.actorRoles,_that.ipAddress,_that.requestId,_that.entityType,_that.entityId,_that.action,_that.diff,_that.context,_that.prevHash,_that.hash,_that.hashValid);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( int seq,  DateTime occurredAt,  String? actorId,  String actorDisplay,  List<String> actorRoles,  String? ipAddress,  String requestId,  String entityType,  String? entityId,  String action,  Map<String, dynamic> diff,  Map<String, dynamic> context,  String prevHash,  String hash,  bool hashValid)?  $default,) {final _that = this;
switch (_that) {
case _AuditEntry() when $default != null:
return $default(_that.seq,_that.occurredAt,_that.actorId,_that.actorDisplay,_that.actorRoles,_that.ipAddress,_that.requestId,_that.entityType,_that.entityId,_that.action,_that.diff,_that.context,_that.prevHash,_that.hash,_that.hashValid);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _AuditEntry implements AuditEntry {
  const _AuditEntry({required this.seq, required this.occurredAt, this.actorId, required this.actorDisplay,  List<String> actorRoles = const <String>[], this.ipAddress, this.requestId = '', required this.entityType, this.entityId, required this.action,  Map<String, dynamic> diff = const <String, dynamic>{},  Map<String, dynamic> context = const <String, dynamic>{}, this.prevHash = '', required this.hash, required this.hashValid}): _actorRoles = actorRoles,_diff = diff,_context = context;
  factory _AuditEntry.fromJson(Map<String, dynamic> json) => _$AuditEntryFromJson(json);

@override final  int seq;
@override final  DateTime occurredAt;
@override final  String? actorId;
@override final  String actorDisplay;
 final  List<String> _actorRoles;
@override@JsonKey() List<String> get actorRoles {
  if (_actorRoles is EqualUnmodifiableListView) return _actorRoles;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_actorRoles);
}

@override final  String? ipAddress;
@override@JsonKey() final  String requestId;
@override final  String entityType;
@override final  String? entityId;
@override final  String action;
 final  Map<String, dynamic> _diff;
@override@JsonKey() Map<String, dynamic> get diff {
  if (_diff is EqualUnmodifiableMapView) return _diff;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_diff);
}

 final  Map<String, dynamic> _context;
@override@JsonKey() Map<String, dynamic> get context {
  if (_context is EqualUnmodifiableMapView) return _context;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_context);
}

@override@JsonKey() final  String prevHash;
@override final  String hash;
@override final  bool hashValid;

/// Create a copy of AuditEntry
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AuditEntryCopyWith<_AuditEntry> get copyWith => __$AuditEntryCopyWithImpl<_AuditEntry>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$AuditEntryToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _AuditEntry&&(identical(other.seq, seq) || other.seq == seq)&&(identical(other.occurredAt, occurredAt) || other.occurredAt == occurredAt)&&(identical(other.actorId, actorId) || other.actorId == actorId)&&(identical(other.actorDisplay, actorDisplay) || other.actorDisplay == actorDisplay)&&const DeepCollectionEquality().equals(other.actorRoles, _actorRoles)&&(identical(other.ipAddress, ipAddress) || other.ipAddress == ipAddress)&&(identical(other.requestId, requestId) || other.requestId == requestId)&&(identical(other.entityType, entityType) || other.entityType == entityType)&&(identical(other.entityId, entityId) || other.entityId == entityId)&&(identical(other.action, action) || other.action == action)&&const DeepCollectionEquality().equals(other.diff, _diff)&&const DeepCollectionEquality().equals(other.context, _context)&&(identical(other.prevHash, prevHash) || other.prevHash == prevHash)&&(identical(other.hash, hash) || other.hash == hash)&&(identical(other.hashValid, hashValid) || other.hashValid == hashValid));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,seq,occurredAt,actorId,actorDisplay,const DeepCollectionEquality().hash(_actorRoles),ipAddress,requestId,entityType,entityId,action,const DeepCollectionEquality().hash(_diff),const DeepCollectionEquality().hash(_context),prevHash,hash,hashValid);
}

@override
String toString() {
    return 'AuditEntry(seq: $seq, occurredAt: $occurredAt, actorId: $actorId, actorDisplay: $actorDisplay, actorRoles: $actorRoles, ipAddress: $ipAddress, requestId: $requestId, entityType: $entityType, entityId: $entityId, action: $action, diff: $diff, context: $context, prevHash: $prevHash, hash: $hash, hashValid: $hashValid)';
}


}

/// @nodoc
abstract mixin class _$AuditEntryCopyWith<$Res> implements $AuditEntryCopyWith<$Res> {
  factory _$AuditEntryCopyWith(_AuditEntry value, $Res Function(_AuditEntry) _then) = __$AuditEntryCopyWithImpl;
@override @useResult
$Res call({
 int seq, DateTime occurredAt, String? actorId, String actorDisplay, List<String> actorRoles, String? ipAddress, String requestId, String entityType, String? entityId, String action, Map<String, dynamic> diff, Map<String, dynamic> context, String prevHash, String hash, bool hashValid
});




}
/// @nodoc
class __$AuditEntryCopyWithImpl<$Res>
    implements _$AuditEntryCopyWith<$Res> {
  __$AuditEntryCopyWithImpl(this._self, this._then);

  final _AuditEntry _self;
  final $Res Function(_AuditEntry) _then;

/// Create a copy of AuditEntry
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? seq = null,Object? occurredAt = null,Object? actorId = freezed,Object? actorDisplay = null,Object? actorRoles = null,Object? ipAddress = freezed,Object? requestId = null,Object? entityType = null,Object? entityId = freezed,Object? action = null,Object? diff = null,Object? context = null,Object? prevHash = null,Object? hash = null,Object? hashValid = null,}) {
  return _then(_AuditEntry(
seq: null == seq ? _self.seq : seq // ignore: cast_nullable_to_non_nullable
as int,occurredAt: null == occurredAt ? _self.occurredAt : occurredAt // ignore: cast_nullable_to_non_nullable
as DateTime,actorId: freezed == actorId ? _self.actorId : actorId // ignore: cast_nullable_to_non_nullable
as String?,actorDisplay: null == actorDisplay ? _self.actorDisplay : actorDisplay // ignore: cast_nullable_to_non_nullable
as String,actorRoles: null == actorRoles ? _self._actorRoles : actorRoles // ignore: cast_nullable_to_non_nullable
as List<String>,ipAddress: freezed == ipAddress ? _self.ipAddress : ipAddress // ignore: cast_nullable_to_non_nullable
as String?,requestId: null == requestId ? _self.requestId : requestId // ignore: cast_nullable_to_non_nullable
as String,entityType: null == entityType ? _self.entityType : entityType // ignore: cast_nullable_to_non_nullable
as String,entityId: freezed == entityId ? _self.entityId : entityId // ignore: cast_nullable_to_non_nullable
as String?,action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,diff: null == diff ? _self._diff : diff // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,context: null == context ? _self._context : context // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,prevHash: null == prevHash ? _self.prevHash : prevHash // ignore: cast_nullable_to_non_nullable
as String,hash: null == hash ? _self.hash : hash // ignore: cast_nullable_to_non_nullable
as String,hashValid: null == hashValid ? _self.hashValid : hashValid // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}


/// @nodoc
mixin _$ChainStatus {

 String get status; bool? get ok; DateTime? get checkedAt; int? get verifiedHeadSeq; int get headSeq;
/// Create a copy of ChainStatus
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ChainStatusCopyWith<ChainStatus> get copyWith => _$ChainStatusCopyWithImpl<ChainStatus>(this as ChainStatus, _$identity);

  /// Serializes this ChainStatus to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ChainStatus;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ChainStatus&&(identical(other.status, _this.status) || other.status == _this.status)&&(identical(other.ok, _this.ok) || other.ok == _this.ok)&&(identical(other.checkedAt, _this.checkedAt) || other.checkedAt == _this.checkedAt)&&(identical(other.verifiedHeadSeq, _this.verifiedHeadSeq) || other.verifiedHeadSeq == _this.verifiedHeadSeq)&&(identical(other.headSeq, _this.headSeq) || other.headSeq == _this.headSeq));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ChainStatus;
  return Object.hash(runtimeType,_this.status,_this.ok,_this.checkedAt,_this.verifiedHeadSeq,_this.headSeq);
}

@override
String toString() {
  final _this = this as ChainStatus;
  return 'ChainStatus(status: ${_this.status}, ok: ${_this.ok}, checkedAt: ${_this.checkedAt}, verifiedHeadSeq: ${_this.verifiedHeadSeq}, headSeq: ${_this.headSeq})';
}


}

/// @nodoc
abstract mixin class $ChainStatusCopyWith<$Res>  {
  factory $ChainStatusCopyWith(ChainStatus value, $Res Function(ChainStatus) _then) = _$ChainStatusCopyWithImpl;
@useResult
$Res call({
 String status, bool? ok, DateTime? checkedAt, int? verifiedHeadSeq, int headSeq
});




}
/// @nodoc
class _$ChainStatusCopyWithImpl<$Res>
    implements $ChainStatusCopyWith<$Res> {
  _$ChainStatusCopyWithImpl(this._self, this._then);

  final ChainStatus _self;
  final $Res Function(ChainStatus) _then;

/// Create a copy of ChainStatus
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? status = null,Object? ok = freezed,Object? checkedAt = freezed,Object? verifiedHeadSeq = freezed,Object? headSeq = null,}) {
  return _then(ChainStatus(
status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,ok: freezed == ok ? _self.ok : ok // ignore: cast_nullable_to_non_nullable
as bool?,checkedAt: freezed == checkedAt ? _self.checkedAt : checkedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,verifiedHeadSeq: freezed == verifiedHeadSeq ? _self.verifiedHeadSeq : verifiedHeadSeq // ignore: cast_nullable_to_non_nullable
as int?,headSeq: null == headSeq ? _self.headSeq : headSeq // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

}


/// Adds pattern-matching-related methods to [ChainStatus].
extension ChainStatusPatterns on ChainStatus {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ChainStatus value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ChainStatus() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ChainStatus value)  $default,){
final _that = this;
switch (_that) {
case _ChainStatus():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ChainStatus value)?  $default,){
final _that = this;
switch (_that) {
case _ChainStatus() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String status,  bool? ok,  DateTime? checkedAt,  int? verifiedHeadSeq,  int headSeq)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ChainStatus() when $default != null:
return $default(_that.status,_that.ok,_that.checkedAt,_that.verifiedHeadSeq,_that.headSeq);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String status,  bool? ok,  DateTime? checkedAt,  int? verifiedHeadSeq,  int headSeq)  $default,) {final _that = this;
switch (_that) {
case _ChainStatus():
return $default(_that.status,_that.ok,_that.checkedAt,_that.verifiedHeadSeq,_that.headSeq);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String status,  bool? ok,  DateTime? checkedAt,  int? verifiedHeadSeq,  int headSeq)?  $default,) {final _that = this;
switch (_that) {
case _ChainStatus() when $default != null:
return $default(_that.status,_that.ok,_that.checkedAt,_that.verifiedHeadSeq,_that.headSeq);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ChainStatus implements ChainStatus {
  const _ChainStatus({required this.status, this.ok, this.checkedAt, this.verifiedHeadSeq, this.headSeq = 0});
  factory _ChainStatus.fromJson(Map<String, dynamic> json) => _$ChainStatusFromJson(json);

@override final  String status;
@override final  bool? ok;
@override final  DateTime? checkedAt;
@override final  int? verifiedHeadSeq;
@override@JsonKey() final  int headSeq;

/// Create a copy of ChainStatus
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ChainStatusCopyWith<_ChainStatus> get copyWith => __$ChainStatusCopyWithImpl<_ChainStatus>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ChainStatusToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ChainStatus&&(identical(other.status, status) || other.status == status)&&(identical(other.ok, ok) || other.ok == ok)&&(identical(other.checkedAt, checkedAt) || other.checkedAt == checkedAt)&&(identical(other.verifiedHeadSeq, verifiedHeadSeq) || other.verifiedHeadSeq == verifiedHeadSeq)&&(identical(other.headSeq, headSeq) || other.headSeq == headSeq));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,status,ok,checkedAt,verifiedHeadSeq,headSeq);
}

@override
String toString() {
    return 'ChainStatus(status: $status, ok: $ok, checkedAt: $checkedAt, verifiedHeadSeq: $verifiedHeadSeq, headSeq: $headSeq)';
}


}

/// @nodoc
abstract mixin class _$ChainStatusCopyWith<$Res> implements $ChainStatusCopyWith<$Res> {
  factory _$ChainStatusCopyWith(_ChainStatus value, $Res Function(_ChainStatus) _then) = __$ChainStatusCopyWithImpl;
@override @useResult
$Res call({
 String status, bool? ok, DateTime? checkedAt, int? verifiedHeadSeq, int headSeq
});




}
/// @nodoc
class __$ChainStatusCopyWithImpl<$Res>
    implements _$ChainStatusCopyWith<$Res> {
  __$ChainStatusCopyWithImpl(this._self, this._then);

  final _ChainStatus _self;
  final $Res Function(_ChainStatus) _then;

/// Create a copy of ChainStatus
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? status = null,Object? ok = freezed,Object? checkedAt = freezed,Object? verifiedHeadSeq = freezed,Object? headSeq = null,}) {
  return _then(_ChainStatus(
status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,ok: freezed == ok ? _self.ok : ok // ignore: cast_nullable_to_non_nullable
as bool?,checkedAt: freezed == checkedAt ? _self.checkedAt : checkedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,verifiedHeadSeq: freezed == verifiedHeadSeq ? _self.verifiedHeadSeq : verifiedHeadSeq // ignore: cast_nullable_to_non_nullable
as int?,headSeq: null == headSeq ? _self.headSeq : headSeq // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}


/// @nodoc
mixin _$Member {

 String get userId; String get displayName; String get email; bool get isActive; List<String> get roles;
/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MemberCopyWith<Member> get copyWith => _$MemberCopyWithImpl<Member>(this as Member, _$identity);

  /// Serializes this Member to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as Member;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Member&&(identical(other.userId, _this.userId) || other.userId == _this.userId)&&(identical(other.displayName, _this.displayName) || other.displayName == _this.displayName)&&(identical(other.email, _this.email) || other.email == _this.email)&&(identical(other.isActive, _this.isActive) || other.isActive == _this.isActive)&&const DeepCollectionEquality().equals(other.roles, _this.roles));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as Member;
  return Object.hash(runtimeType,_this.userId,_this.displayName,_this.email,_this.isActive,const DeepCollectionEquality().hash(_this.roles));
}

@override
String toString() {
  final _this = this as Member;
  return 'Member(userId: ${_this.userId}, displayName: ${_this.displayName}, email: ${_this.email}, isActive: ${_this.isActive}, roles: ${_this.roles})';
}


}

/// @nodoc
abstract mixin class $MemberCopyWith<$Res>  {
  factory $MemberCopyWith(Member value, $Res Function(Member) _then) = _$MemberCopyWithImpl;
@useResult
$Res call({
 String userId, String displayName, String email, bool isActive, List<String> roles
});




}
/// @nodoc
class _$MemberCopyWithImpl<$Res>
    implements $MemberCopyWith<$Res> {
  _$MemberCopyWithImpl(this._self, this._then);

  final Member _self;
  final $Res Function(Member) _then;

/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? userId = null,Object? displayName = null,Object? email = null,Object? isActive = null,Object? roles = null,}) {
  return _then(Member(
userId: null == userId ? _self.userId : userId // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,email: null == email ? _self.email : email // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,roles: null == roles ? _self.roles : roles // ignore: cast_nullable_to_non_nullable
as List<String>,
  ));
}

}


/// Adds pattern-matching-related methods to [Member].
extension MemberPatterns on Member {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Member value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Member() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Member value)  $default,){
final _that = this;
switch (_that) {
case _Member():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Member value)?  $default,){
final _that = this;
switch (_that) {
case _Member() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String userId,  String displayName,  String email,  bool isActive,  List<String> roles)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Member() when $default != null:
return $default(_that.userId,_that.displayName,_that.email,_that.isActive,_that.roles);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String userId,  String displayName,  String email,  bool isActive,  List<String> roles)  $default,) {final _that = this;
switch (_that) {
case _Member():
return $default(_that.userId,_that.displayName,_that.email,_that.isActive,_that.roles);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String userId,  String displayName,  String email,  bool isActive,  List<String> roles)?  $default,) {final _that = this;
switch (_that) {
case _Member() when $default != null:
return $default(_that.userId,_that.displayName,_that.email,_that.isActive,_that.roles);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Member extends Member {
  const _Member({required this.userId, required this.displayName, this.email = '', this.isActive = true,  List<String> roles = const <String>[]}): _roles = roles,super._();
  factory _Member.fromJson(Map<String, dynamic> json) => _$MemberFromJson(json);

@override final  String userId;
@override final  String displayName;
@override@JsonKey() final  String email;
@override@JsonKey() final  bool isActive;
 final  List<String> _roles;
@override@JsonKey() List<String> get roles {
  if (_roles is EqualUnmodifiableListView) return _roles;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_roles);
}


/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MemberCopyWith<_Member> get copyWith => __$MemberCopyWithImpl<_Member>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$MemberToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _Member&&(identical(other.userId, userId) || other.userId == userId)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.email, email) || other.email == email)&&(identical(other.isActive, isActive) || other.isActive == isActive)&&const DeepCollectionEquality().equals(other.roles, _roles));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,userId,displayName,email,isActive,const DeepCollectionEquality().hash(_roles));
}

@override
String toString() {
    return 'Member(userId: $userId, displayName: $displayName, email: $email, isActive: $isActive, roles: $roles)';
}


}

/// @nodoc
abstract mixin class _$MemberCopyWith<$Res> implements $MemberCopyWith<$Res> {
  factory _$MemberCopyWith(_Member value, $Res Function(_Member) _then) = __$MemberCopyWithImpl;
@override @useResult
$Res call({
 String userId, String displayName, String email, bool isActive, List<String> roles
});




}
/// @nodoc
class __$MemberCopyWithImpl<$Res>
    implements _$MemberCopyWith<$Res> {
  __$MemberCopyWithImpl(this._self, this._then);

  final _Member _self;
  final $Res Function(_Member) _then;

/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? userId = null,Object? displayName = null,Object? email = null,Object? isActive = null,Object? roles = null,}) {
  return _then(_Member(
userId: null == userId ? _self.userId : userId // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,email: null == email ? _self.email : email // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,roles: null == roles ? _self._roles : roles // ignore: cast_nullable_to_non_nullable
as List<String>,
  ));
}


}


/// @nodoc
mixin _$CompanyCategory {

 String get categoryId; String get code; String get name; bool get requiresApproval; String get defaultRisk; bool get isActive; String? get approverOverrideId;
/// Create a copy of CompanyCategory
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CompanyCategoryCopyWith<CompanyCategory> get copyWith => _$CompanyCategoryCopyWithImpl<CompanyCategory>(this as CompanyCategory, _$identity);

  /// Serializes this CompanyCategory to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as CompanyCategory;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CompanyCategory&&(identical(other.categoryId, _this.categoryId) || other.categoryId == _this.categoryId)&&(identical(other.code, _this.code) || other.code == _this.code)&&(identical(other.name, _this.name) || other.name == _this.name)&&(identical(other.requiresApproval, _this.requiresApproval) || other.requiresApproval == _this.requiresApproval)&&(identical(other.defaultRisk, _this.defaultRisk) || other.defaultRisk == _this.defaultRisk)&&(identical(other.isActive, _this.isActive) || other.isActive == _this.isActive)&&(identical(other.approverOverrideId, _this.approverOverrideId) || other.approverOverrideId == _this.approverOverrideId));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as CompanyCategory;
  return Object.hash(runtimeType,_this.categoryId,_this.code,_this.name,_this.requiresApproval,_this.defaultRisk,_this.isActive,_this.approverOverrideId);
}

@override
String toString() {
  final _this = this as CompanyCategory;
  return 'CompanyCategory(categoryId: ${_this.categoryId}, code: ${_this.code}, name: ${_this.name}, requiresApproval: ${_this.requiresApproval}, defaultRisk: ${_this.defaultRisk}, isActive: ${_this.isActive}, approverOverrideId: ${_this.approverOverrideId})';
}


}

/// @nodoc
abstract mixin class $CompanyCategoryCopyWith<$Res>  {
  factory $CompanyCategoryCopyWith(CompanyCategory value, $Res Function(CompanyCategory) _then) = _$CompanyCategoryCopyWithImpl;
@useResult
$Res call({
 String categoryId, String code, String name, bool requiresApproval, String defaultRisk, bool isActive, String? approverOverrideId
});




}
/// @nodoc
class _$CompanyCategoryCopyWithImpl<$Res>
    implements $CompanyCategoryCopyWith<$Res> {
  _$CompanyCategoryCopyWithImpl(this._self, this._then);

  final CompanyCategory _self;
  final $Res Function(CompanyCategory) _then;

/// Create a copy of CompanyCategory
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? categoryId = null,Object? code = null,Object? name = null,Object? requiresApproval = null,Object? defaultRisk = null,Object? isActive = null,Object? approverOverrideId = freezed,}) {
  return _then(CompanyCategory(
categoryId: null == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String,code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,requiresApproval: null == requiresApproval ? _self.requiresApproval : requiresApproval // ignore: cast_nullable_to_non_nullable
as bool,defaultRisk: null == defaultRisk ? _self.defaultRisk : defaultRisk // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,approverOverrideId: freezed == approverOverrideId ? _self.approverOverrideId : approverOverrideId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [CompanyCategory].
extension CompanyCategoryPatterns on CompanyCategory {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CompanyCategory value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CompanyCategory() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CompanyCategory value)  $default,){
final _that = this;
switch (_that) {
case _CompanyCategory():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CompanyCategory value)?  $default,){
final _that = this;
switch (_that) {
case _CompanyCategory() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String categoryId,  String code,  String name,  bool requiresApproval,  String defaultRisk,  bool isActive,  String? approverOverrideId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CompanyCategory() when $default != null:
return $default(_that.categoryId,_that.code,_that.name,_that.requiresApproval,_that.defaultRisk,_that.isActive,_that.approverOverrideId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String categoryId,  String code,  String name,  bool requiresApproval,  String defaultRisk,  bool isActive,  String? approverOverrideId)  $default,) {final _that = this;
switch (_that) {
case _CompanyCategory():
return $default(_that.categoryId,_that.code,_that.name,_that.requiresApproval,_that.defaultRisk,_that.isActive,_that.approverOverrideId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String categoryId,  String code,  String name,  bool requiresApproval,  String defaultRisk,  bool isActive,  String? approverOverrideId)?  $default,) {final _that = this;
switch (_that) {
case _CompanyCategory() when $default != null:
return $default(_that.categoryId,_that.code,_that.name,_that.requiresApproval,_that.defaultRisk,_that.isActive,_that.approverOverrideId);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _CompanyCategory implements CompanyCategory {
  const _CompanyCategory({required this.categoryId, required this.code, required this.name, this.requiresApproval = true, this.defaultRisk = 'medium', this.isActive = true, this.approverOverrideId});
  factory _CompanyCategory.fromJson(Map<String, dynamic> json) => _$CompanyCategoryFromJson(json);

@override final  String categoryId;
@override final  String code;
@override final  String name;
@override@JsonKey() final  bool requiresApproval;
@override@JsonKey() final  String defaultRisk;
@override@JsonKey() final  bool isActive;
@override final  String? approverOverrideId;

/// Create a copy of CompanyCategory
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CompanyCategoryCopyWith<_CompanyCategory> get copyWith => __$CompanyCategoryCopyWithImpl<_CompanyCategory>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$CompanyCategoryToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _CompanyCategory&&(identical(other.categoryId, categoryId) || other.categoryId == categoryId)&&(identical(other.code, code) || other.code == code)&&(identical(other.name, name) || other.name == name)&&(identical(other.requiresApproval, requiresApproval) || other.requiresApproval == requiresApproval)&&(identical(other.defaultRisk, defaultRisk) || other.defaultRisk == defaultRisk)&&(identical(other.isActive, isActive) || other.isActive == isActive)&&(identical(other.approverOverrideId, approverOverrideId) || other.approverOverrideId == approverOverrideId));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,categoryId,code,name,requiresApproval,defaultRisk,isActive,approverOverrideId);
}

@override
String toString() {
    return 'CompanyCategory(categoryId: $categoryId, code: $code, name: $name, requiresApproval: $requiresApproval, defaultRisk: $defaultRisk, isActive: $isActive, approverOverrideId: $approverOverrideId)';
}


}

/// @nodoc
abstract mixin class _$CompanyCategoryCopyWith<$Res> implements $CompanyCategoryCopyWith<$Res> {
  factory _$CompanyCategoryCopyWith(_CompanyCategory value, $Res Function(_CompanyCategory) _then) = __$CompanyCategoryCopyWithImpl;
@override @useResult
$Res call({
 String categoryId, String code, String name, bool requiresApproval, String defaultRisk, bool isActive, String? approverOverrideId
});




}
/// @nodoc
class __$CompanyCategoryCopyWithImpl<$Res>
    implements _$CompanyCategoryCopyWith<$Res> {
  __$CompanyCategoryCopyWithImpl(this._self, this._then);

  final _CompanyCategory _self;
  final $Res Function(_CompanyCategory) _then;

/// Create a copy of CompanyCategory
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? categoryId = null,Object? code = null,Object? name = null,Object? requiresApproval = null,Object? defaultRisk = null,Object? isActive = null,Object? approverOverrideId = freezed,}) {
  return _then(_CompanyCategory(
categoryId: null == categoryId ? _self.categoryId : categoryId // ignore: cast_nullable_to_non_nullable
as String,code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,requiresApproval: null == requiresApproval ? _self.requiresApproval : requiresApproval // ignore: cast_nullable_to_non_nullable
as bool,defaultRisk: null == defaultRisk ? _self.defaultRisk : defaultRisk // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,approverOverrideId: freezed == approverOverrideId ? _self.approverOverrideId : approverOverrideId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}


/// @nodoc
mixin _$Category {

 String get id; String get code; String get name; String? get parentId; bool get requiresApproval; bool get requiresCiOwnerConsent; String get defaultRisk; bool get isActive;
/// Create a copy of Category
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CategoryCopyWith<Category> get copyWith => _$CategoryCopyWithImpl<Category>(this as Category, _$identity);

  /// Serializes this Category to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as Category;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Category&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.code, _this.code) || other.code == _this.code)&&(identical(other.name, _this.name) || other.name == _this.name)&&(identical(other.parentId, _this.parentId) || other.parentId == _this.parentId)&&(identical(other.requiresApproval, _this.requiresApproval) || other.requiresApproval == _this.requiresApproval)&&(identical(other.requiresCiOwnerConsent, _this.requiresCiOwnerConsent) || other.requiresCiOwnerConsent == _this.requiresCiOwnerConsent)&&(identical(other.defaultRisk, _this.defaultRisk) || other.defaultRisk == _this.defaultRisk)&&(identical(other.isActive, _this.isActive) || other.isActive == _this.isActive));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as Category;
  return Object.hash(runtimeType,_this.id,_this.code,_this.name,_this.parentId,_this.requiresApproval,_this.requiresCiOwnerConsent,_this.defaultRisk,_this.isActive);
}

@override
String toString() {
  final _this = this as Category;
  return 'Category(id: ${_this.id}, code: ${_this.code}, name: ${_this.name}, parentId: ${_this.parentId}, requiresApproval: ${_this.requiresApproval}, requiresCiOwnerConsent: ${_this.requiresCiOwnerConsent}, defaultRisk: ${_this.defaultRisk}, isActive: ${_this.isActive})';
}


}

/// @nodoc
abstract mixin class $CategoryCopyWith<$Res>  {
  factory $CategoryCopyWith(Category value, $Res Function(Category) _then) = _$CategoryCopyWithImpl;
@useResult
$Res call({
 String id, String code, String name, String? parentId, bool requiresApproval, bool requiresCiOwnerConsent, String defaultRisk, bool isActive
});




}
/// @nodoc
class _$CategoryCopyWithImpl<$Res>
    implements $CategoryCopyWith<$Res> {
  _$CategoryCopyWithImpl(this._self, this._then);

  final Category _self;
  final $Res Function(Category) _then;

/// Create a copy of Category
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? code = null,Object? name = null,Object? parentId = freezed,Object? requiresApproval = null,Object? requiresCiOwnerConsent = null,Object? defaultRisk = null,Object? isActive = null,}) {
  return _then(Category(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,parentId: freezed == parentId ? _self.parentId : parentId // ignore: cast_nullable_to_non_nullable
as String?,requiresApproval: null == requiresApproval ? _self.requiresApproval : requiresApproval // ignore: cast_nullable_to_non_nullable
as bool,requiresCiOwnerConsent: null == requiresCiOwnerConsent ? _self.requiresCiOwnerConsent : requiresCiOwnerConsent // ignore: cast_nullable_to_non_nullable
as bool,defaultRisk: null == defaultRisk ? _self.defaultRisk : defaultRisk // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [Category].
extension CategoryPatterns on Category {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Category value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Category() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Category value)  $default,){
final _that = this;
switch (_that) {
case _Category():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Category value)?  $default,){
final _that = this;
switch (_that) {
case _Category() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String code,  String name,  String? parentId,  bool requiresApproval,  bool requiresCiOwnerConsent,  String defaultRisk,  bool isActive)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Category() when $default != null:
return $default(_that.id,_that.code,_that.name,_that.parentId,_that.requiresApproval,_that.requiresCiOwnerConsent,_that.defaultRisk,_that.isActive);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String code,  String name,  String? parentId,  bool requiresApproval,  bool requiresCiOwnerConsent,  String defaultRisk,  bool isActive)  $default,) {final _that = this;
switch (_that) {
case _Category():
return $default(_that.id,_that.code,_that.name,_that.parentId,_that.requiresApproval,_that.requiresCiOwnerConsent,_that.defaultRisk,_that.isActive);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String code,  String name,  String? parentId,  bool requiresApproval,  bool requiresCiOwnerConsent,  String defaultRisk,  bool isActive)?  $default,) {final _that = this;
switch (_that) {
case _Category() when $default != null:
return $default(_that.id,_that.code,_that.name,_that.parentId,_that.requiresApproval,_that.requiresCiOwnerConsent,_that.defaultRisk,_that.isActive);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Category implements Category {
  const _Category({required this.id, required this.code, required this.name, this.parentId, this.requiresApproval = true, this.requiresCiOwnerConsent = false, this.defaultRisk = 'medium', this.isActive = true});
  factory _Category.fromJson(Map<String, dynamic> json) => _$CategoryFromJson(json);

@override final  String id;
@override final  String code;
@override final  String name;
@override final  String? parentId;
@override@JsonKey() final  bool requiresApproval;
@override@JsonKey() final  bool requiresCiOwnerConsent;
@override@JsonKey() final  String defaultRisk;
@override@JsonKey() final  bool isActive;

/// Create a copy of Category
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CategoryCopyWith<_Category> get copyWith => __$CategoryCopyWithImpl<_Category>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$CategoryToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _Category&&(identical(other.id, id) || other.id == id)&&(identical(other.code, code) || other.code == code)&&(identical(other.name, name) || other.name == name)&&(identical(other.parentId, parentId) || other.parentId == parentId)&&(identical(other.requiresApproval, requiresApproval) || other.requiresApproval == requiresApproval)&&(identical(other.requiresCiOwnerConsent, requiresCiOwnerConsent) || other.requiresCiOwnerConsent == requiresCiOwnerConsent)&&(identical(other.defaultRisk, defaultRisk) || other.defaultRisk == defaultRisk)&&(identical(other.isActive, isActive) || other.isActive == isActive));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,code,name,parentId,requiresApproval,requiresCiOwnerConsent,defaultRisk,isActive);
}

@override
String toString() {
    return 'Category(id: $id, code: $code, name: $name, parentId: $parentId, requiresApproval: $requiresApproval, requiresCiOwnerConsent: $requiresCiOwnerConsent, defaultRisk: $defaultRisk, isActive: $isActive)';
}


}

/// @nodoc
abstract mixin class _$CategoryCopyWith<$Res> implements $CategoryCopyWith<$Res> {
  factory _$CategoryCopyWith(_Category value, $Res Function(_Category) _then) = __$CategoryCopyWithImpl;
@override @useResult
$Res call({
 String id, String code, String name, String? parentId, bool requiresApproval, bool requiresCiOwnerConsent, String defaultRisk, bool isActive
});




}
/// @nodoc
class __$CategoryCopyWithImpl<$Res>
    implements _$CategoryCopyWith<$Res> {
  __$CategoryCopyWithImpl(this._self, this._then);

  final _Category _self;
  final $Res Function(_Category) _then;

/// Create a copy of Category
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? code = null,Object? name = null,Object? parentId = freezed,Object? requiresApproval = null,Object? requiresCiOwnerConsent = null,Object? defaultRisk = null,Object? isActive = null,}) {
  return _then(_Category(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,parentId: freezed == parentId ? _self.parentId : parentId // ignore: cast_nullable_to_non_nullable
as String?,requiresApproval: null == requiresApproval ? _self.requiresApproval : requiresApproval // ignore: cast_nullable_to_non_nullable
as bool,requiresCiOwnerConsent: null == requiresCiOwnerConsent ? _self.requiresCiOwnerConsent : requiresCiOwnerConsent // ignore: cast_nullable_to_non_nullable
as bool,defaultRisk: null == defaultRisk ? _self.defaultRisk : defaultRisk // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}


/// @nodoc
mixin _$CiItem {

 String get id; String get companyId; String get ciTypeId; String get ciTypeCode; String get ciTypeName; String get identifier; String get name; String? get description; String? get ownerUserId; bool get isActive;
/// Create a copy of CiItem
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CiItemCopyWith<CiItem> get copyWith => _$CiItemCopyWithImpl<CiItem>(this as CiItem, _$identity);

  /// Serializes this CiItem to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as CiItem;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CiItem&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.companyId, _this.companyId) || other.companyId == _this.companyId)&&(identical(other.ciTypeId, _this.ciTypeId) || other.ciTypeId == _this.ciTypeId)&&(identical(other.ciTypeCode, _this.ciTypeCode) || other.ciTypeCode == _this.ciTypeCode)&&(identical(other.ciTypeName, _this.ciTypeName) || other.ciTypeName == _this.ciTypeName)&&(identical(other.identifier, _this.identifier) || other.identifier == _this.identifier)&&(identical(other.name, _this.name) || other.name == _this.name)&&(identical(other.description, _this.description) || other.description == _this.description)&&(identical(other.ownerUserId, _this.ownerUserId) || other.ownerUserId == _this.ownerUserId)&&(identical(other.isActive, _this.isActive) || other.isActive == _this.isActive));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as CiItem;
  return Object.hash(runtimeType,_this.id,_this.companyId,_this.ciTypeId,_this.ciTypeCode,_this.ciTypeName,_this.identifier,_this.name,_this.description,_this.ownerUserId,_this.isActive);
}

@override
String toString() {
  final _this = this as CiItem;
  return 'CiItem(id: ${_this.id}, companyId: ${_this.companyId}, ciTypeId: ${_this.ciTypeId}, ciTypeCode: ${_this.ciTypeCode}, ciTypeName: ${_this.ciTypeName}, identifier: ${_this.identifier}, name: ${_this.name}, description: ${_this.description}, ownerUserId: ${_this.ownerUserId}, isActive: ${_this.isActive})';
}


}

/// @nodoc
abstract mixin class $CiItemCopyWith<$Res>  {
  factory $CiItemCopyWith(CiItem value, $Res Function(CiItem) _then) = _$CiItemCopyWithImpl;
@useResult
$Res call({
 String id, String companyId, String ciTypeId, String ciTypeCode, String ciTypeName, String identifier, String name, String? description, String? ownerUserId, bool isActive
});




}
/// @nodoc
class _$CiItemCopyWithImpl<$Res>
    implements $CiItemCopyWith<$Res> {
  _$CiItemCopyWithImpl(this._self, this._then);

  final CiItem _self;
  final $Res Function(CiItem) _then;

/// Create a copy of CiItem
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? companyId = null,Object? ciTypeId = null,Object? ciTypeCode = null,Object? ciTypeName = null,Object? identifier = null,Object? name = null,Object? description = freezed,Object? ownerUserId = freezed,Object? isActive = null,}) {
  return _then(CiItem(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,companyId: null == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String,ciTypeId: null == ciTypeId ? _self.ciTypeId : ciTypeId // ignore: cast_nullable_to_non_nullable
as String,ciTypeCode: null == ciTypeCode ? _self.ciTypeCode : ciTypeCode // ignore: cast_nullable_to_non_nullable
as String,ciTypeName: null == ciTypeName ? _self.ciTypeName : ciTypeName // ignore: cast_nullable_to_non_nullable
as String,identifier: null == identifier ? _self.identifier : identifier // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,ownerUserId: freezed == ownerUserId ? _self.ownerUserId : ownerUserId // ignore: cast_nullable_to_non_nullable
as String?,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [CiItem].
extension CiItemPatterns on CiItem {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CiItem value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CiItem() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CiItem value)  $default,){
final _that = this;
switch (_that) {
case _CiItem():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CiItem value)?  $default,){
final _that = this;
switch (_that) {
case _CiItem() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String companyId,  String ciTypeId,  String ciTypeCode,  String ciTypeName,  String identifier,  String name,  String? description,  String? ownerUserId,  bool isActive)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CiItem() when $default != null:
return $default(_that.id,_that.companyId,_that.ciTypeId,_that.ciTypeCode,_that.ciTypeName,_that.identifier,_that.name,_that.description,_that.ownerUserId,_that.isActive);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String companyId,  String ciTypeId,  String ciTypeCode,  String ciTypeName,  String identifier,  String name,  String? description,  String? ownerUserId,  bool isActive)  $default,) {final _that = this;
switch (_that) {
case _CiItem():
return $default(_that.id,_that.companyId,_that.ciTypeId,_that.ciTypeCode,_that.ciTypeName,_that.identifier,_that.name,_that.description,_that.ownerUserId,_that.isActive);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String companyId,  String ciTypeId,  String ciTypeCode,  String ciTypeName,  String identifier,  String name,  String? description,  String? ownerUserId,  bool isActive)?  $default,) {final _that = this;
switch (_that) {
case _CiItem() when $default != null:
return $default(_that.id,_that.companyId,_that.ciTypeId,_that.ciTypeCode,_that.ciTypeName,_that.identifier,_that.name,_that.description,_that.ownerUserId,_that.isActive);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _CiItem implements CiItem {
  const _CiItem({required this.id, required this.companyId, required this.ciTypeId, this.ciTypeCode = '', this.ciTypeName = '', required this.identifier, required this.name, this.description, this.ownerUserId, this.isActive = true});
  factory _CiItem.fromJson(Map<String, dynamic> json) => _$CiItemFromJson(json);

@override final  String id;
@override final  String companyId;
@override final  String ciTypeId;
@override@JsonKey() final  String ciTypeCode;
@override@JsonKey() final  String ciTypeName;
@override final  String identifier;
@override final  String name;
@override final  String? description;
@override final  String? ownerUserId;
@override@JsonKey() final  bool isActive;

/// Create a copy of CiItem
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CiItemCopyWith<_CiItem> get copyWith => __$CiItemCopyWithImpl<_CiItem>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$CiItemToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _CiItem&&(identical(other.id, id) || other.id == id)&&(identical(other.companyId, companyId) || other.companyId == companyId)&&(identical(other.ciTypeId, ciTypeId) || other.ciTypeId == ciTypeId)&&(identical(other.ciTypeCode, ciTypeCode) || other.ciTypeCode == ciTypeCode)&&(identical(other.ciTypeName, ciTypeName) || other.ciTypeName == ciTypeName)&&(identical(other.identifier, identifier) || other.identifier == identifier)&&(identical(other.name, name) || other.name == name)&&(identical(other.description, description) || other.description == description)&&(identical(other.ownerUserId, ownerUserId) || other.ownerUserId == ownerUserId)&&(identical(other.isActive, isActive) || other.isActive == isActive));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,companyId,ciTypeId,ciTypeCode,ciTypeName,identifier,name,description,ownerUserId,isActive);
}

@override
String toString() {
    return 'CiItem(id: $id, companyId: $companyId, ciTypeId: $ciTypeId, ciTypeCode: $ciTypeCode, ciTypeName: $ciTypeName, identifier: $identifier, name: $name, description: $description, ownerUserId: $ownerUserId, isActive: $isActive)';
}


}

/// @nodoc
abstract mixin class _$CiItemCopyWith<$Res> implements $CiItemCopyWith<$Res> {
  factory _$CiItemCopyWith(_CiItem value, $Res Function(_CiItem) _then) = __$CiItemCopyWithImpl;
@override @useResult
$Res call({
 String id, String companyId, String ciTypeId, String ciTypeCode, String ciTypeName, String identifier, String name, String? description, String? ownerUserId, bool isActive
});




}
/// @nodoc
class __$CiItemCopyWithImpl<$Res>
    implements _$CiItemCopyWith<$Res> {
  __$CiItemCopyWithImpl(this._self, this._then);

  final _CiItem _self;
  final $Res Function(_CiItem) _then;

/// Create a copy of CiItem
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? companyId = null,Object? ciTypeId = null,Object? ciTypeCode = null,Object? ciTypeName = null,Object? identifier = null,Object? name = null,Object? description = freezed,Object? ownerUserId = freezed,Object? isActive = null,}) {
  return _then(_CiItem(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,companyId: null == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String,ciTypeId: null == ciTypeId ? _self.ciTypeId : ciTypeId // ignore: cast_nullable_to_non_nullable
as String,ciTypeCode: null == ciTypeCode ? _self.ciTypeCode : ciTypeCode // ignore: cast_nullable_to_non_nullable
as String,ciTypeName: null == ciTypeName ? _self.ciTypeName : ciTypeName // ignore: cast_nullable_to_non_nullable
as String,identifier: null == identifier ? _self.identifier : identifier // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,ownerUserId: freezed == ownerUserId ? _self.ownerUserId : ownerUserId // ignore: cast_nullable_to_non_nullable
as String?,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}


/// @nodoc
mixin _$CiType {

 String get id; String get code; String get name; bool get isActive;
/// Create a copy of CiType
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CiTypeCopyWith<CiType> get copyWith => _$CiTypeCopyWithImpl<CiType>(this as CiType, _$identity);

  /// Serializes this CiType to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as CiType;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CiType&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.code, _this.code) || other.code == _this.code)&&(identical(other.name, _this.name) || other.name == _this.name)&&(identical(other.isActive, _this.isActive) || other.isActive == _this.isActive));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as CiType;
  return Object.hash(runtimeType,_this.id,_this.code,_this.name,_this.isActive);
}

@override
String toString() {
  final _this = this as CiType;
  return 'CiType(id: ${_this.id}, code: ${_this.code}, name: ${_this.name}, isActive: ${_this.isActive})';
}


}

/// @nodoc
abstract mixin class $CiTypeCopyWith<$Res>  {
  factory $CiTypeCopyWith(CiType value, $Res Function(CiType) _then) = _$CiTypeCopyWithImpl;
@useResult
$Res call({
 String id, String code, String name, bool isActive
});




}
/// @nodoc
class _$CiTypeCopyWithImpl<$Res>
    implements $CiTypeCopyWith<$Res> {
  _$CiTypeCopyWithImpl(this._self, this._then);

  final CiType _self;
  final $Res Function(CiType) _then;

/// Create a copy of CiType
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? code = null,Object? name = null,Object? isActive = null,}) {
  return _then(CiType(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [CiType].
extension CiTypePatterns on CiType {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CiType value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CiType() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CiType value)  $default,){
final _that = this;
switch (_that) {
case _CiType():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CiType value)?  $default,){
final _that = this;
switch (_that) {
case _CiType() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String code,  String name,  bool isActive)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CiType() when $default != null:
return $default(_that.id,_that.code,_that.name,_that.isActive);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String code,  String name,  bool isActive)  $default,) {final _that = this;
switch (_that) {
case _CiType():
return $default(_that.id,_that.code,_that.name,_that.isActive);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String code,  String name,  bool isActive)?  $default,) {final _that = this;
switch (_that) {
case _CiType() when $default != null:
return $default(_that.id,_that.code,_that.name,_that.isActive);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _CiType implements CiType {
  const _CiType({required this.id, required this.code, required this.name, this.isActive = true});
  factory _CiType.fromJson(Map<String, dynamic> json) => _$CiTypeFromJson(json);

@override final  String id;
@override final  String code;
@override final  String name;
@override@JsonKey() final  bool isActive;

/// Create a copy of CiType
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CiTypeCopyWith<_CiType> get copyWith => __$CiTypeCopyWithImpl<_CiType>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$CiTypeToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _CiType&&(identical(other.id, id) || other.id == id)&&(identical(other.code, code) || other.code == code)&&(identical(other.name, name) || other.name == name)&&(identical(other.isActive, isActive) || other.isActive == isActive));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,code,name,isActive);
}

@override
String toString() {
    return 'CiType(id: $id, code: $code, name: $name, isActive: $isActive)';
}


}

/// @nodoc
abstract mixin class _$CiTypeCopyWith<$Res> implements $CiTypeCopyWith<$Res> {
  factory _$CiTypeCopyWith(_CiType value, $Res Function(_CiType) _then) = __$CiTypeCopyWithImpl;
@override @useResult
$Res call({
 String id, String code, String name, bool isActive
});




}
/// @nodoc
class __$CiTypeCopyWithImpl<$Res>
    implements _$CiTypeCopyWith<$Res> {
  __$CiTypeCopyWithImpl(this._self, this._then);

  final _CiType _self;
  final $Res Function(_CiType) _then;

/// Create a copy of CiType
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? code = null,Object? name = null,Object? isActive = null,}) {
  return _then(_CiType(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,code: null == code ? _self.code : code // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}

// dart format on
