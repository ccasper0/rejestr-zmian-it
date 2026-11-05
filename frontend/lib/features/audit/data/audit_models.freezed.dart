// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'audit_models.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$AuditLogEntry {

 int get id; String? get companyId; int get seq; DateTime get occurredAt; String? get actorId; String get actorDisplay; List<String> get actorRoles; String? get ipAddress; String? get userAgent; String get requestId; String get entityType; String? get entityId; String get action; Map<String, dynamic> get diff; Map<String, dynamic> get context; String get prevHash; String get hash;
/// Create a copy of AuditLogEntry
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AuditLogEntryCopyWith<AuditLogEntry> get copyWith => _$AuditLogEntryCopyWithImpl<AuditLogEntry>(this as AuditLogEntry, _$identity);

  /// Serializes this AuditLogEntry to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as AuditLogEntry;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AuditLogEntry&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.companyId, _this.companyId) || other.companyId == _this.companyId)&&(identical(other.seq, _this.seq) || other.seq == _this.seq)&&(identical(other.occurredAt, _this.occurredAt) || other.occurredAt == _this.occurredAt)&&(identical(other.actorId, _this.actorId) || other.actorId == _this.actorId)&&(identical(other.actorDisplay, _this.actorDisplay) || other.actorDisplay == _this.actorDisplay)&&const DeepCollectionEquality().equals(other.actorRoles, _this.actorRoles)&&(identical(other.ipAddress, _this.ipAddress) || other.ipAddress == _this.ipAddress)&&(identical(other.userAgent, _this.userAgent) || other.userAgent == _this.userAgent)&&(identical(other.requestId, _this.requestId) || other.requestId == _this.requestId)&&(identical(other.entityType, _this.entityType) || other.entityType == _this.entityType)&&(identical(other.entityId, _this.entityId) || other.entityId == _this.entityId)&&(identical(other.action, _this.action) || other.action == _this.action)&&const DeepCollectionEquality().equals(other.diff, _this.diff)&&const DeepCollectionEquality().equals(other.context, _this.context)&&(identical(other.prevHash, _this.prevHash) || other.prevHash == _this.prevHash)&&(identical(other.hash, _this.hash) || other.hash == _this.hash));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as AuditLogEntry;
  return Object.hash(runtimeType,_this.id,_this.companyId,_this.seq,_this.occurredAt,_this.actorId,_this.actorDisplay,const DeepCollectionEquality().hash(_this.actorRoles),_this.ipAddress,_this.userAgent,_this.requestId,_this.entityType,_this.entityId,_this.action,const DeepCollectionEquality().hash(_this.diff),const DeepCollectionEquality().hash(_this.context),_this.prevHash,_this.hash);
}

@override
String toString() {
  final _this = this as AuditLogEntry;
  return 'AuditLogEntry(id: ${_this.id}, companyId: ${_this.companyId}, seq: ${_this.seq}, occurredAt: ${_this.occurredAt}, actorId: ${_this.actorId}, actorDisplay: ${_this.actorDisplay}, actorRoles: ${_this.actorRoles}, ipAddress: ${_this.ipAddress}, userAgent: ${_this.userAgent}, requestId: ${_this.requestId}, entityType: ${_this.entityType}, entityId: ${_this.entityId}, action: ${_this.action}, diff: ${_this.diff}, context: ${_this.context}, prevHash: ${_this.prevHash}, hash: ${_this.hash})';
}


}

/// @nodoc
abstract mixin class $AuditLogEntryCopyWith<$Res>  {
  factory $AuditLogEntryCopyWith(AuditLogEntry value, $Res Function(AuditLogEntry) _then) = _$AuditLogEntryCopyWithImpl;
@useResult
$Res call({
 int id, String? companyId, int seq, DateTime occurredAt, String? actorId, String actorDisplay, List<String> actorRoles, String? ipAddress, String? userAgent, String requestId, String entityType, String? entityId, String action, Map<String, dynamic> diff, Map<String, dynamic> context, String prevHash, String hash
});




}
/// @nodoc
class _$AuditLogEntryCopyWithImpl<$Res>
    implements $AuditLogEntryCopyWith<$Res> {
  _$AuditLogEntryCopyWithImpl(this._self, this._then);

  final AuditLogEntry _self;
  final $Res Function(AuditLogEntry) _then;

/// Create a copy of AuditLogEntry
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? companyId = freezed,Object? seq = null,Object? occurredAt = null,Object? actorId = freezed,Object? actorDisplay = null,Object? actorRoles = null,Object? ipAddress = freezed,Object? userAgent = freezed,Object? requestId = null,Object? entityType = null,Object? entityId = freezed,Object? action = null,Object? diff = null,Object? context = null,Object? prevHash = null,Object? hash = null,}) {
  return _then(AuditLogEntry(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as int,companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,seq: null == seq ? _self.seq : seq // ignore: cast_nullable_to_non_nullable
as int,occurredAt: null == occurredAt ? _self.occurredAt : occurredAt // ignore: cast_nullable_to_non_nullable
as DateTime,actorId: freezed == actorId ? _self.actorId : actorId // ignore: cast_nullable_to_non_nullable
as String?,actorDisplay: null == actorDisplay ? _self.actorDisplay : actorDisplay // ignore: cast_nullable_to_non_nullable
as String,actorRoles: null == actorRoles ? _self.actorRoles : actorRoles // ignore: cast_nullable_to_non_nullable
as List<String>,ipAddress: freezed == ipAddress ? _self.ipAddress : ipAddress // ignore: cast_nullable_to_non_nullable
as String?,userAgent: freezed == userAgent ? _self.userAgent : userAgent // ignore: cast_nullable_to_non_nullable
as String?,requestId: null == requestId ? _self.requestId : requestId // ignore: cast_nullable_to_non_nullable
as String,entityType: null == entityType ? _self.entityType : entityType // ignore: cast_nullable_to_non_nullable
as String,entityId: freezed == entityId ? _self.entityId : entityId // ignore: cast_nullable_to_non_nullable
as String?,action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,diff: null == diff ? _self.diff : diff // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,context: null == context ? _self.context : context // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,prevHash: null == prevHash ? _self.prevHash : prevHash // ignore: cast_nullable_to_non_nullable
as String,hash: null == hash ? _self.hash : hash // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

}


/// Adds pattern-matching-related methods to [AuditLogEntry].
extension AuditLogEntryPatterns on AuditLogEntry {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AuditLogEntry value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AuditLogEntry() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AuditLogEntry value)  $default,){
final _that = this;
switch (_that) {
case _AuditLogEntry():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AuditLogEntry value)?  $default,){
final _that = this;
switch (_that) {
case _AuditLogEntry() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( int id,  String? companyId,  int seq,  DateTime occurredAt,  String? actorId,  String actorDisplay,  List<String> actorRoles,  String? ipAddress,  String? userAgent,  String requestId,  String entityType,  String? entityId,  String action,  Map<String, dynamic> diff,  Map<String, dynamic> context,  String prevHash,  String hash)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AuditLogEntry() when $default != null:
return $default(_that.id,_that.companyId,_that.seq,_that.occurredAt,_that.actorId,_that.actorDisplay,_that.actorRoles,_that.ipAddress,_that.userAgent,_that.requestId,_that.entityType,_that.entityId,_that.action,_that.diff,_that.context,_that.prevHash,_that.hash);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( int id,  String? companyId,  int seq,  DateTime occurredAt,  String? actorId,  String actorDisplay,  List<String> actorRoles,  String? ipAddress,  String? userAgent,  String requestId,  String entityType,  String? entityId,  String action,  Map<String, dynamic> diff,  Map<String, dynamic> context,  String prevHash,  String hash)  $default,) {final _that = this;
switch (_that) {
case _AuditLogEntry():
return $default(_that.id,_that.companyId,_that.seq,_that.occurredAt,_that.actorId,_that.actorDisplay,_that.actorRoles,_that.ipAddress,_that.userAgent,_that.requestId,_that.entityType,_that.entityId,_that.action,_that.diff,_that.context,_that.prevHash,_that.hash);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( int id,  String? companyId,  int seq,  DateTime occurredAt,  String? actorId,  String actorDisplay,  List<String> actorRoles,  String? ipAddress,  String? userAgent,  String requestId,  String entityType,  String? entityId,  String action,  Map<String, dynamic> diff,  Map<String, dynamic> context,  String prevHash,  String hash)?  $default,) {final _that = this;
switch (_that) {
case _AuditLogEntry() when $default != null:
return $default(_that.id,_that.companyId,_that.seq,_that.occurredAt,_that.actorId,_that.actorDisplay,_that.actorRoles,_that.ipAddress,_that.userAgent,_that.requestId,_that.entityType,_that.entityId,_that.action,_that.diff,_that.context,_that.prevHash,_that.hash);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _AuditLogEntry implements AuditLogEntry {
  const _AuditLogEntry({required this.id, this.companyId, required this.seq, required this.occurredAt, this.actorId, required this.actorDisplay,  List<String> actorRoles = const <String>[], this.ipAddress, this.userAgent, required this.requestId, required this.entityType, this.entityId, required this.action,  Map<String, dynamic> diff = const <String, dynamic>{},  Map<String, dynamic> context = const <String, dynamic>{}, required this.prevHash, required this.hash}): _actorRoles = actorRoles,_diff = diff,_context = context;
  factory _AuditLogEntry.fromJson(Map<String, dynamic> json) => _$AuditLogEntryFromJson(json);

@override final  int id;
@override final  String? companyId;
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
@override final  String? userAgent;
@override final  String requestId;
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

@override final  String prevHash;
@override final  String hash;

/// Create a copy of AuditLogEntry
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AuditLogEntryCopyWith<_AuditLogEntry> get copyWith => __$AuditLogEntryCopyWithImpl<_AuditLogEntry>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$AuditLogEntryToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _AuditLogEntry&&(identical(other.id, id) || other.id == id)&&(identical(other.companyId, companyId) || other.companyId == companyId)&&(identical(other.seq, seq) || other.seq == seq)&&(identical(other.occurredAt, occurredAt) || other.occurredAt == occurredAt)&&(identical(other.actorId, actorId) || other.actorId == actorId)&&(identical(other.actorDisplay, actorDisplay) || other.actorDisplay == actorDisplay)&&const DeepCollectionEquality().equals(other.actorRoles, _actorRoles)&&(identical(other.ipAddress, ipAddress) || other.ipAddress == ipAddress)&&(identical(other.userAgent, userAgent) || other.userAgent == userAgent)&&(identical(other.requestId, requestId) || other.requestId == requestId)&&(identical(other.entityType, entityType) || other.entityType == entityType)&&(identical(other.entityId, entityId) || other.entityId == entityId)&&(identical(other.action, action) || other.action == action)&&const DeepCollectionEquality().equals(other.diff, _diff)&&const DeepCollectionEquality().equals(other.context, _context)&&(identical(other.prevHash, prevHash) || other.prevHash == prevHash)&&(identical(other.hash, hash) || other.hash == hash));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,companyId,seq,occurredAt,actorId,actorDisplay,const DeepCollectionEquality().hash(_actorRoles),ipAddress,userAgent,requestId,entityType,entityId,action,const DeepCollectionEquality().hash(_diff),const DeepCollectionEquality().hash(_context),prevHash,hash);
}

@override
String toString() {
    return 'AuditLogEntry(id: $id, companyId: $companyId, seq: $seq, occurredAt: $occurredAt, actorId: $actorId, actorDisplay: $actorDisplay, actorRoles: $actorRoles, ipAddress: $ipAddress, userAgent: $userAgent, requestId: $requestId, entityType: $entityType, entityId: $entityId, action: $action, diff: $diff, context: $context, prevHash: $prevHash, hash: $hash)';
}


}

/// @nodoc
abstract mixin class _$AuditLogEntryCopyWith<$Res> implements $AuditLogEntryCopyWith<$Res> {
  factory _$AuditLogEntryCopyWith(_AuditLogEntry value, $Res Function(_AuditLogEntry) _then) = __$AuditLogEntryCopyWithImpl;
@override @useResult
$Res call({
 int id, String? companyId, int seq, DateTime occurredAt, String? actorId, String actorDisplay, List<String> actorRoles, String? ipAddress, String? userAgent, String requestId, String entityType, String? entityId, String action, Map<String, dynamic> diff, Map<String, dynamic> context, String prevHash, String hash
});




}
/// @nodoc
class __$AuditLogEntryCopyWithImpl<$Res>
    implements _$AuditLogEntryCopyWith<$Res> {
  __$AuditLogEntryCopyWithImpl(this._self, this._then);

  final _AuditLogEntry _self;
  final $Res Function(_AuditLogEntry) _then;

/// Create a copy of AuditLogEntry
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? companyId = freezed,Object? seq = null,Object? occurredAt = null,Object? actorId = freezed,Object? actorDisplay = null,Object? actorRoles = null,Object? ipAddress = freezed,Object? userAgent = freezed,Object? requestId = null,Object? entityType = null,Object? entityId = freezed,Object? action = null,Object? diff = null,Object? context = null,Object? prevHash = null,Object? hash = null,}) {
  return _then(_AuditLogEntry(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as int,companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,seq: null == seq ? _self.seq : seq // ignore: cast_nullable_to_non_nullable
as int,occurredAt: null == occurredAt ? _self.occurredAt : occurredAt // ignore: cast_nullable_to_non_nullable
as DateTime,actorId: freezed == actorId ? _self.actorId : actorId // ignore: cast_nullable_to_non_nullable
as String?,actorDisplay: null == actorDisplay ? _self.actorDisplay : actorDisplay // ignore: cast_nullable_to_non_nullable
as String,actorRoles: null == actorRoles ? _self._actorRoles : actorRoles // ignore: cast_nullable_to_non_nullable
as List<String>,ipAddress: freezed == ipAddress ? _self.ipAddress : ipAddress // ignore: cast_nullable_to_non_nullable
as String?,userAgent: freezed == userAgent ? _self.userAgent : userAgent // ignore: cast_nullable_to_non_nullable
as String?,requestId: null == requestId ? _self.requestId : requestId // ignore: cast_nullable_to_non_nullable
as String,entityType: null == entityType ? _self.entityType : entityType // ignore: cast_nullable_to_non_nullable
as String,entityId: freezed == entityId ? _self.entityId : entityId // ignore: cast_nullable_to_non_nullable
as String?,action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,diff: null == diff ? _self._diff : diff // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,context: null == context ? _self._context : context // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,prevHash: null == prevHash ? _self.prevHash : prevHash // ignore: cast_nullable_to_non_nullable
as String,hash: null == hash ? _self.hash : hash // ignore: cast_nullable_to_non_nullable
as String,
  ));
}


}


/// @nodoc
mixin _$AuditEntryRef {

 String? get companyId; int get seq; String get hash;
/// Create a copy of AuditEntryRef
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AuditEntryRefCopyWith<AuditEntryRef> get copyWith => _$AuditEntryRefCopyWithImpl<AuditEntryRef>(this as AuditEntryRef, _$identity);

  /// Serializes this AuditEntryRef to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as AuditEntryRef;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AuditEntryRef&&(identical(other.companyId, _this.companyId) || other.companyId == _this.companyId)&&(identical(other.seq, _this.seq) || other.seq == _this.seq)&&(identical(other.hash, _this.hash) || other.hash == _this.hash));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as AuditEntryRef;
  return Object.hash(runtimeType,_this.companyId,_this.seq,_this.hash);
}

@override
String toString() {
  final _this = this as AuditEntryRef;
  return 'AuditEntryRef(companyId: ${_this.companyId}, seq: ${_this.seq}, hash: ${_this.hash})';
}


}

/// @nodoc
abstract mixin class $AuditEntryRefCopyWith<$Res>  {
  factory $AuditEntryRefCopyWith(AuditEntryRef value, $Res Function(AuditEntryRef) _then) = _$AuditEntryRefCopyWithImpl;
@useResult
$Res call({
 String? companyId, int seq, String hash
});




}
/// @nodoc
class _$AuditEntryRefCopyWithImpl<$Res>
    implements $AuditEntryRefCopyWith<$Res> {
  _$AuditEntryRefCopyWithImpl(this._self, this._then);

  final AuditEntryRef _self;
  final $Res Function(AuditEntryRef) _then;

/// Create a copy of AuditEntryRef
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? companyId = freezed,Object? seq = null,Object? hash = null,}) {
  return _then(AuditEntryRef(
companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,seq: null == seq ? _self.seq : seq // ignore: cast_nullable_to_non_nullable
as int,hash: null == hash ? _self.hash : hash // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

}


/// Adds pattern-matching-related methods to [AuditEntryRef].
extension AuditEntryRefPatterns on AuditEntryRef {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AuditEntryRef value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AuditEntryRef() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AuditEntryRef value)  $default,){
final _that = this;
switch (_that) {
case _AuditEntryRef():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AuditEntryRef value)?  $default,){
final _that = this;
switch (_that) {
case _AuditEntryRef() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String? companyId,  int seq,  String hash)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AuditEntryRef() when $default != null:
return $default(_that.companyId,_that.seq,_that.hash);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String? companyId,  int seq,  String hash)  $default,) {final _that = this;
switch (_that) {
case _AuditEntryRef():
return $default(_that.companyId,_that.seq,_that.hash);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String? companyId,  int seq,  String hash)?  $default,) {final _that = this;
switch (_that) {
case _AuditEntryRef() when $default != null:
return $default(_that.companyId,_that.seq,_that.hash);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _AuditEntryRef implements AuditEntryRef {
  const _AuditEntryRef({this.companyId, required this.seq, required this.hash});
  factory _AuditEntryRef.fromJson(Map<String, dynamic> json) => _$AuditEntryRefFromJson(json);

@override final  String? companyId;
@override final  int seq;
@override final  String hash;

/// Create a copy of AuditEntryRef
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AuditEntryRefCopyWith<_AuditEntryRef> get copyWith => __$AuditEntryRefCopyWithImpl<_AuditEntryRef>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$AuditEntryRefToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _AuditEntryRef&&(identical(other.companyId, companyId) || other.companyId == companyId)&&(identical(other.seq, seq) || other.seq == seq)&&(identical(other.hash, hash) || other.hash == hash));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,companyId,seq,hash);
}

@override
String toString() {
    return 'AuditEntryRef(companyId: $companyId, seq: $seq, hash: $hash)';
}


}

/// @nodoc
abstract mixin class _$AuditEntryRefCopyWith<$Res> implements $AuditEntryRefCopyWith<$Res> {
  factory _$AuditEntryRefCopyWith(_AuditEntryRef value, $Res Function(_AuditEntryRef) _then) = __$AuditEntryRefCopyWithImpl;
@override @useResult
$Res call({
 String? companyId, int seq, String hash
});




}
/// @nodoc
class __$AuditEntryRefCopyWithImpl<$Res>
    implements _$AuditEntryRefCopyWith<$Res> {
  __$AuditEntryRefCopyWithImpl(this._self, this._then);

  final _AuditEntryRef _self;
  final $Res Function(_AuditEntryRef) _then;

/// Create a copy of AuditEntryRef
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? companyId = freezed,Object? seq = null,Object? hash = null,}) {
  return _then(_AuditEntryRef(
companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,seq: null == seq ? _self.seq : seq // ignore: cast_nullable_to_non_nullable
as int,hash: null == hash ? _self.hash : hash // ignore: cast_nullable_to_non_nullable
as String,
  ));
}


}


/// @nodoc
mixin _$VerifyResult {

 String? get companyId; String get chain; bool get ok; int get checked; int? get firstBrokenSeq; int get headSeq; String get headHash; DateTime? get verifiedAt; String? get recordedIn; AuditEntryRef? get auditEntry;
/// Create a copy of VerifyResult
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$VerifyResultCopyWith<VerifyResult> get copyWith => _$VerifyResultCopyWithImpl<VerifyResult>(this as VerifyResult, _$identity);

  /// Serializes this VerifyResult to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as VerifyResult;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is VerifyResult&&(identical(other.companyId, _this.companyId) || other.companyId == _this.companyId)&&(identical(other.chain, _this.chain) || other.chain == _this.chain)&&(identical(other.ok, _this.ok) || other.ok == _this.ok)&&(identical(other.checked, _this.checked) || other.checked == _this.checked)&&(identical(other.firstBrokenSeq, _this.firstBrokenSeq) || other.firstBrokenSeq == _this.firstBrokenSeq)&&(identical(other.headSeq, _this.headSeq) || other.headSeq == _this.headSeq)&&(identical(other.headHash, _this.headHash) || other.headHash == _this.headHash)&&(identical(other.verifiedAt, _this.verifiedAt) || other.verifiedAt == _this.verifiedAt)&&(identical(other.recordedIn, _this.recordedIn) || other.recordedIn == _this.recordedIn)&&(identical(other.auditEntry, _this.auditEntry) || other.auditEntry == _this.auditEntry));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as VerifyResult;
  return Object.hash(runtimeType,_this.companyId,_this.chain,_this.ok,_this.checked,_this.firstBrokenSeq,_this.headSeq,_this.headHash,_this.verifiedAt,_this.recordedIn,_this.auditEntry);
}

@override
String toString() {
  final _this = this as VerifyResult;
  return 'VerifyResult(companyId: ${_this.companyId}, chain: ${_this.chain}, ok: ${_this.ok}, checked: ${_this.checked}, firstBrokenSeq: ${_this.firstBrokenSeq}, headSeq: ${_this.headSeq}, headHash: ${_this.headHash}, verifiedAt: ${_this.verifiedAt}, recordedIn: ${_this.recordedIn}, auditEntry: ${_this.auditEntry})';
}


}

/// @nodoc
abstract mixin class $VerifyResultCopyWith<$Res>  {
  factory $VerifyResultCopyWith(VerifyResult value, $Res Function(VerifyResult) _then) = _$VerifyResultCopyWithImpl;
@useResult
$Res call({
 String? companyId, String chain, bool ok, int checked, int? firstBrokenSeq, int headSeq, String headHash, DateTime? verifiedAt, String? recordedIn, AuditEntryRef? auditEntry
});


$AuditEntryRefCopyWith<$Res>? get auditEntry;

}
/// @nodoc
class _$VerifyResultCopyWithImpl<$Res>
    implements $VerifyResultCopyWith<$Res> {
  _$VerifyResultCopyWithImpl(this._self, this._then);

  final VerifyResult _self;
  final $Res Function(VerifyResult) _then;

/// Create a copy of VerifyResult
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? companyId = freezed,Object? chain = null,Object? ok = null,Object? checked = null,Object? firstBrokenSeq = freezed,Object? headSeq = null,Object? headHash = null,Object? verifiedAt = freezed,Object? recordedIn = freezed,Object? auditEntry = freezed,}) {
  return _then(VerifyResult(
companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,chain: null == chain ? _self.chain : chain // ignore: cast_nullable_to_non_nullable
as String,ok: null == ok ? _self.ok : ok // ignore: cast_nullable_to_non_nullable
as bool,checked: null == checked ? _self.checked : checked // ignore: cast_nullable_to_non_nullable
as int,firstBrokenSeq: freezed == firstBrokenSeq ? _self.firstBrokenSeq : firstBrokenSeq // ignore: cast_nullable_to_non_nullable
as int?,headSeq: null == headSeq ? _self.headSeq : headSeq // ignore: cast_nullable_to_non_nullable
as int,headHash: null == headHash ? _self.headHash : headHash // ignore: cast_nullable_to_non_nullable
as String,verifiedAt: freezed == verifiedAt ? _self.verifiedAt : verifiedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,recordedIn: freezed == recordedIn ? _self.recordedIn : recordedIn // ignore: cast_nullable_to_non_nullable
as String?,auditEntry: freezed == auditEntry ? _self.auditEntry : auditEntry // ignore: cast_nullable_to_non_nullable
as AuditEntryRef?,
  ));
}
/// Create a copy of VerifyResult
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$AuditEntryRefCopyWith<$Res>? get auditEntry {
    if (_self.auditEntry == null) {
    return null;
  }

  return $AuditEntryRefCopyWith<$Res>(_self.auditEntry!, (value) {
    return _then(_self.copyWith(auditEntry: value));
  });
}
}


/// Adds pattern-matching-related methods to [VerifyResult].
extension VerifyResultPatterns on VerifyResult {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _VerifyResult value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _VerifyResult() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _VerifyResult value)  $default,){
final _that = this;
switch (_that) {
case _VerifyResult():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _VerifyResult value)?  $default,){
final _that = this;
switch (_that) {
case _VerifyResult() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String? companyId,  String chain,  bool ok,  int checked,  int? firstBrokenSeq,  int headSeq,  String headHash,  DateTime? verifiedAt,  String? recordedIn,  AuditEntryRef? auditEntry)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _VerifyResult() when $default != null:
return $default(_that.companyId,_that.chain,_that.ok,_that.checked,_that.firstBrokenSeq,_that.headSeq,_that.headHash,_that.verifiedAt,_that.recordedIn,_that.auditEntry);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String? companyId,  String chain,  bool ok,  int checked,  int? firstBrokenSeq,  int headSeq,  String headHash,  DateTime? verifiedAt,  String? recordedIn,  AuditEntryRef? auditEntry)  $default,) {final _that = this;
switch (_that) {
case _VerifyResult():
return $default(_that.companyId,_that.chain,_that.ok,_that.checked,_that.firstBrokenSeq,_that.headSeq,_that.headHash,_that.verifiedAt,_that.recordedIn,_that.auditEntry);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String? companyId,  String chain,  bool ok,  int checked,  int? firstBrokenSeq,  int headSeq,  String headHash,  DateTime? verifiedAt,  String? recordedIn,  AuditEntryRef? auditEntry)?  $default,) {final _that = this;
switch (_that) {
case _VerifyResult() when $default != null:
return $default(_that.companyId,_that.chain,_that.ok,_that.checked,_that.firstBrokenSeq,_that.headSeq,_that.headHash,_that.verifiedAt,_that.recordedIn,_that.auditEntry);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _VerifyResult implements VerifyResult {
  const _VerifyResult({this.companyId, required this.chain, required this.ok, required this.checked, this.firstBrokenSeq, required this.headSeq, required this.headHash, this.verifiedAt, this.recordedIn, this.auditEntry});
  factory _VerifyResult.fromJson(Map<String, dynamic> json) => _$VerifyResultFromJson(json);

@override final  String? companyId;
@override final  String chain;
@override final  bool ok;
@override final  int checked;
@override final  int? firstBrokenSeq;
@override final  int headSeq;
@override final  String headHash;
@override final  DateTime? verifiedAt;
@override final  String? recordedIn;
@override final  AuditEntryRef? auditEntry;

/// Create a copy of VerifyResult
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$VerifyResultCopyWith<_VerifyResult> get copyWith => __$VerifyResultCopyWithImpl<_VerifyResult>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$VerifyResultToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _VerifyResult&&(identical(other.companyId, companyId) || other.companyId == companyId)&&(identical(other.chain, chain) || other.chain == chain)&&(identical(other.ok, ok) || other.ok == ok)&&(identical(other.checked, checked) || other.checked == checked)&&(identical(other.firstBrokenSeq, firstBrokenSeq) || other.firstBrokenSeq == firstBrokenSeq)&&(identical(other.headSeq, headSeq) || other.headSeq == headSeq)&&(identical(other.headHash, headHash) || other.headHash == headHash)&&(identical(other.verifiedAt, verifiedAt) || other.verifiedAt == verifiedAt)&&(identical(other.recordedIn, recordedIn) || other.recordedIn == recordedIn)&&(identical(other.auditEntry, auditEntry) || other.auditEntry == auditEntry));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,companyId,chain,ok,checked,firstBrokenSeq,headSeq,headHash,verifiedAt,recordedIn,auditEntry);
}

@override
String toString() {
    return 'VerifyResult(companyId: $companyId, chain: $chain, ok: $ok, checked: $checked, firstBrokenSeq: $firstBrokenSeq, headSeq: $headSeq, headHash: $headHash, verifiedAt: $verifiedAt, recordedIn: $recordedIn, auditEntry: $auditEntry)';
}


}

/// @nodoc
abstract mixin class _$VerifyResultCopyWith<$Res> implements $VerifyResultCopyWith<$Res> {
  factory _$VerifyResultCopyWith(_VerifyResult value, $Res Function(_VerifyResult) _then) = __$VerifyResultCopyWithImpl;
@override @useResult
$Res call({
 String? companyId, String chain, bool ok, int checked, int? firstBrokenSeq, int headSeq, String headHash, DateTime? verifiedAt, String? recordedIn, AuditEntryRef? auditEntry
});


@override $AuditEntryRefCopyWith<$Res>? get auditEntry;

}
/// @nodoc
class __$VerifyResultCopyWithImpl<$Res>
    implements _$VerifyResultCopyWith<$Res> {
  __$VerifyResultCopyWithImpl(this._self, this._then);

  final _VerifyResult _self;
  final $Res Function(_VerifyResult) _then;

/// Create a copy of VerifyResult
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? companyId = freezed,Object? chain = null,Object? ok = null,Object? checked = null,Object? firstBrokenSeq = freezed,Object? headSeq = null,Object? headHash = null,Object? verifiedAt = freezed,Object? recordedIn = freezed,Object? auditEntry = freezed,}) {
  return _then(_VerifyResult(
companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,chain: null == chain ? _self.chain : chain // ignore: cast_nullable_to_non_nullable
as String,ok: null == ok ? _self.ok : ok // ignore: cast_nullable_to_non_nullable
as bool,checked: null == checked ? _self.checked : checked // ignore: cast_nullable_to_non_nullable
as int,firstBrokenSeq: freezed == firstBrokenSeq ? _self.firstBrokenSeq : firstBrokenSeq // ignore: cast_nullable_to_non_nullable
as int?,headSeq: null == headSeq ? _self.headSeq : headSeq // ignore: cast_nullable_to_non_nullable
as int,headHash: null == headHash ? _self.headHash : headHash // ignore: cast_nullable_to_non_nullable
as String,verifiedAt: freezed == verifiedAt ? _self.verifiedAt : verifiedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,recordedIn: freezed == recordedIn ? _self.recordedIn : recordedIn // ignore: cast_nullable_to_non_nullable
as String?,auditEntry: freezed == auditEntry ? _self.auditEntry : auditEntry // ignore: cast_nullable_to_non_nullable
as AuditEntryRef?,
  ));
}

/// Create a copy of VerifyResult
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$AuditEntryRefCopyWith<$Res>? get auditEntry {
    if (_self.auditEntry == null) {
    return null;
  }

  return $AuditEntryRefCopyWith<$Res>(_self.auditEntry!, (value) {
    return _then(_self.copyWith(auditEntry: value));
  });
}
}

// dart format on
