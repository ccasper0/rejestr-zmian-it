// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'admin_models.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$CompanyCounts {

 int get activeCi; int get allCi; int get editors; int get approvers; int get auditors; int get viewers;
/// Create a copy of CompanyCounts
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CompanyCountsCopyWith<CompanyCounts> get copyWith => _$CompanyCountsCopyWithImpl<CompanyCounts>(this as CompanyCounts, _$identity);

  /// Serializes this CompanyCounts to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as CompanyCounts;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CompanyCounts&&(identical(other.activeCi, _this.activeCi) || other.activeCi == _this.activeCi)&&(identical(other.allCi, _this.allCi) || other.allCi == _this.allCi)&&(identical(other.editors, _this.editors) || other.editors == _this.editors)&&(identical(other.approvers, _this.approvers) || other.approvers == _this.approvers)&&(identical(other.auditors, _this.auditors) || other.auditors == _this.auditors)&&(identical(other.viewers, _this.viewers) || other.viewers == _this.viewers));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as CompanyCounts;
  return Object.hash(runtimeType,_this.activeCi,_this.allCi,_this.editors,_this.approvers,_this.auditors,_this.viewers);
}

@override
String toString() {
  final _this = this as CompanyCounts;
  return 'CompanyCounts(activeCi: ${_this.activeCi}, allCi: ${_this.allCi}, editors: ${_this.editors}, approvers: ${_this.approvers}, auditors: ${_this.auditors}, viewers: ${_this.viewers})';
}


}

/// @nodoc
abstract mixin class $CompanyCountsCopyWith<$Res>  {
  factory $CompanyCountsCopyWith(CompanyCounts value, $Res Function(CompanyCounts) _then) = _$CompanyCountsCopyWithImpl;
@useResult
$Res call({
 int activeCi, int allCi, int editors, int approvers, int auditors, int viewers
});




}
/// @nodoc
class _$CompanyCountsCopyWithImpl<$Res>
    implements $CompanyCountsCopyWith<$Res> {
  _$CompanyCountsCopyWithImpl(this._self, this._then);

  final CompanyCounts _self;
  final $Res Function(CompanyCounts) _then;

/// Create a copy of CompanyCounts
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? activeCi = null,Object? allCi = null,Object? editors = null,Object? approvers = null,Object? auditors = null,Object? viewers = null,}) {
  return _then(CompanyCounts(
activeCi: null == activeCi ? _self.activeCi : activeCi // ignore: cast_nullable_to_non_nullable
as int,allCi: null == allCi ? _self.allCi : allCi // ignore: cast_nullable_to_non_nullable
as int,editors: null == editors ? _self.editors : editors // ignore: cast_nullable_to_non_nullable
as int,approvers: null == approvers ? _self.approvers : approvers // ignore: cast_nullable_to_non_nullable
as int,auditors: null == auditors ? _self.auditors : auditors // ignore: cast_nullable_to_non_nullable
as int,viewers: null == viewers ? _self.viewers : viewers // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

}


/// Adds pattern-matching-related methods to [CompanyCounts].
extension CompanyCountsPatterns on CompanyCounts {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CompanyCounts value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CompanyCounts() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CompanyCounts value)  $default,){
final _that = this;
switch (_that) {
case _CompanyCounts():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CompanyCounts value)?  $default,){
final _that = this;
switch (_that) {
case _CompanyCounts() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( int activeCi,  int allCi,  int editors,  int approvers,  int auditors,  int viewers)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CompanyCounts() when $default != null:
return $default(_that.activeCi,_that.allCi,_that.editors,_that.approvers,_that.auditors,_that.viewers);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( int activeCi,  int allCi,  int editors,  int approvers,  int auditors,  int viewers)  $default,) {final _that = this;
switch (_that) {
case _CompanyCounts():
return $default(_that.activeCi,_that.allCi,_that.editors,_that.approvers,_that.auditors,_that.viewers);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( int activeCi,  int allCi,  int editors,  int approvers,  int auditors,  int viewers)?  $default,) {final _that = this;
switch (_that) {
case _CompanyCounts() when $default != null:
return $default(_that.activeCi,_that.allCi,_that.editors,_that.approvers,_that.auditors,_that.viewers);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _CompanyCounts implements CompanyCounts {
  const _CompanyCounts({this.activeCi = 0, this.allCi = 0, this.editors = 0, this.approvers = 0, this.auditors = 0, this.viewers = 0});
  factory _CompanyCounts.fromJson(Map<String, dynamic> json) => _$CompanyCountsFromJson(json);

@override@JsonKey() final  int activeCi;
@override@JsonKey() final  int allCi;
@override@JsonKey() final  int editors;
@override@JsonKey() final  int approvers;
@override@JsonKey() final  int auditors;
@override@JsonKey() final  int viewers;

/// Create a copy of CompanyCounts
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CompanyCountsCopyWith<_CompanyCounts> get copyWith => __$CompanyCountsCopyWithImpl<_CompanyCounts>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$CompanyCountsToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _CompanyCounts&&(identical(other.activeCi, activeCi) || other.activeCi == activeCi)&&(identical(other.allCi, allCi) || other.allCi == allCi)&&(identical(other.editors, editors) || other.editors == editors)&&(identical(other.approvers, approvers) || other.approvers == approvers)&&(identical(other.auditors, auditors) || other.auditors == auditors)&&(identical(other.viewers, viewers) || other.viewers == viewers));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,activeCi,allCi,editors,approvers,auditors,viewers);
}

@override
String toString() {
    return 'CompanyCounts(activeCi: $activeCi, allCi: $allCi, editors: $editors, approvers: $approvers, auditors: $auditors, viewers: $viewers)';
}


}

/// @nodoc
abstract mixin class _$CompanyCountsCopyWith<$Res> implements $CompanyCountsCopyWith<$Res> {
  factory _$CompanyCountsCopyWith(_CompanyCounts value, $Res Function(_CompanyCounts) _then) = __$CompanyCountsCopyWithImpl;
@override @useResult
$Res call({
 int activeCi, int allCi, int editors, int approvers, int auditors, int viewers
});




}
/// @nodoc
class __$CompanyCountsCopyWithImpl<$Res>
    implements _$CompanyCountsCopyWith<$Res> {
  __$CompanyCountsCopyWithImpl(this._self, this._then);

  final _CompanyCounts _self;
  final $Res Function(_CompanyCounts) _then;

/// Create a copy of CompanyCounts
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? activeCi = null,Object? allCi = null,Object? editors = null,Object? approvers = null,Object? auditors = null,Object? viewers = null,}) {
  return _then(_CompanyCounts(
activeCi: null == activeCi ? _self.activeCi : activeCi // ignore: cast_nullable_to_non_nullable
as int,allCi: null == allCi ? _self.allCi : allCi // ignore: cast_nullable_to_non_nullable
as int,editors: null == editors ? _self.editors : editors // ignore: cast_nullable_to_non_nullable
as int,approvers: null == approvers ? _self.approvers : approvers // ignore: cast_nullable_to_non_nullable
as int,auditors: null == auditors ? _self.auditors : auditors // ignore: cast_nullable_to_non_nullable
as int,viewers: null == viewers ? _self.viewers : viewers // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}


/// @nodoc
mixin _$AdminCompany {

 String get id; String get name; String? get taxId; String get prefix; String get status; bool get isKscEntity; String? get defaultApproverId; DateTime get createdAt; DateTime get updatedAt; List<String> get myRoles; CompanyCounts get counts;
/// Create a copy of AdminCompany
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AdminCompanyCopyWith<AdminCompany> get copyWith => _$AdminCompanyCopyWithImpl<AdminCompany>(this as AdminCompany, _$identity);

  /// Serializes this AdminCompany to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as AdminCompany;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AdminCompany&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.name, _this.name) || other.name == _this.name)&&(identical(other.taxId, _this.taxId) || other.taxId == _this.taxId)&&(identical(other.prefix, _this.prefix) || other.prefix == _this.prefix)&&(identical(other.status, _this.status) || other.status == _this.status)&&(identical(other.isKscEntity, _this.isKscEntity) || other.isKscEntity == _this.isKscEntity)&&(identical(other.defaultApproverId, _this.defaultApproverId) || other.defaultApproverId == _this.defaultApproverId)&&(identical(other.createdAt, _this.createdAt) || other.createdAt == _this.createdAt)&&(identical(other.updatedAt, _this.updatedAt) || other.updatedAt == _this.updatedAt)&&const DeepCollectionEquality().equals(other.myRoles, _this.myRoles)&&(identical(other.counts, _this.counts) || other.counts == _this.counts));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as AdminCompany;
  return Object.hash(runtimeType,_this.id,_this.name,_this.taxId,_this.prefix,_this.status,_this.isKscEntity,_this.defaultApproverId,_this.createdAt,_this.updatedAt,const DeepCollectionEquality().hash(_this.myRoles),_this.counts);
}

@override
String toString() {
  final _this = this as AdminCompany;
  return 'AdminCompany(id: ${_this.id}, name: ${_this.name}, taxId: ${_this.taxId}, prefix: ${_this.prefix}, status: ${_this.status}, isKscEntity: ${_this.isKscEntity}, defaultApproverId: ${_this.defaultApproverId}, createdAt: ${_this.createdAt}, updatedAt: ${_this.updatedAt}, myRoles: ${_this.myRoles}, counts: ${_this.counts})';
}


}

/// @nodoc
abstract mixin class $AdminCompanyCopyWith<$Res>  {
  factory $AdminCompanyCopyWith(AdminCompany value, $Res Function(AdminCompany) _then) = _$AdminCompanyCopyWithImpl;
@useResult
$Res call({
 String id, String name, String? taxId, String prefix, String status, bool isKscEntity, String? defaultApproverId, DateTime createdAt, DateTime updatedAt, List<String> myRoles, CompanyCounts counts
});


$CompanyCountsCopyWith<$Res> get counts;

}
/// @nodoc
class _$AdminCompanyCopyWithImpl<$Res>
    implements $AdminCompanyCopyWith<$Res> {
  _$AdminCompanyCopyWithImpl(this._self, this._then);

  final AdminCompany _self;
  final $Res Function(AdminCompany) _then;

/// Create a copy of AdminCompany
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? name = null,Object? taxId = freezed,Object? prefix = null,Object? status = null,Object? isKscEntity = null,Object? defaultApproverId = freezed,Object? createdAt = null,Object? updatedAt = null,Object? myRoles = null,Object? counts = null,}) {
  return _then(AdminCompany(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,taxId: freezed == taxId ? _self.taxId : taxId // ignore: cast_nullable_to_non_nullable
as String?,prefix: null == prefix ? _self.prefix : prefix // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,isKscEntity: null == isKscEntity ? _self.isKscEntity : isKscEntity // ignore: cast_nullable_to_non_nullable
as bool,defaultApproverId: freezed == defaultApproverId ? _self.defaultApproverId : defaultApproverId // ignore: cast_nullable_to_non_nullable
as String?,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,updatedAt: null == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime,myRoles: null == myRoles ? _self.myRoles : myRoles // ignore: cast_nullable_to_non_nullable
as List<String>,counts: null == counts ? _self.counts : counts // ignore: cast_nullable_to_non_nullable
as CompanyCounts,
  ));
}
/// Create a copy of AdminCompany
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$CompanyCountsCopyWith<$Res> get counts {
  
  return $CompanyCountsCopyWith<$Res>(_self.counts, (value) {
    return _then(_self.copyWith(counts: value));
  });
}
}


/// Adds pattern-matching-related methods to [AdminCompany].
extension AdminCompanyPatterns on AdminCompany {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AdminCompany value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AdminCompany() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AdminCompany value)  $default,){
final _that = this;
switch (_that) {
case _AdminCompany():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AdminCompany value)?  $default,){
final _that = this;
switch (_that) {
case _AdminCompany() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String name,  String? taxId,  String prefix,  String status,  bool isKscEntity,  String? defaultApproverId,  DateTime createdAt,  DateTime updatedAt,  List<String> myRoles,  CompanyCounts counts)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AdminCompany() when $default != null:
return $default(_that.id,_that.name,_that.taxId,_that.prefix,_that.status,_that.isKscEntity,_that.defaultApproverId,_that.createdAt,_that.updatedAt,_that.myRoles,_that.counts);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String name,  String? taxId,  String prefix,  String status,  bool isKscEntity,  String? defaultApproverId,  DateTime createdAt,  DateTime updatedAt,  List<String> myRoles,  CompanyCounts counts)  $default,) {final _that = this;
switch (_that) {
case _AdminCompany():
return $default(_that.id,_that.name,_that.taxId,_that.prefix,_that.status,_that.isKscEntity,_that.defaultApproverId,_that.createdAt,_that.updatedAt,_that.myRoles,_that.counts);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String name,  String? taxId,  String prefix,  String status,  bool isKscEntity,  String? defaultApproverId,  DateTime createdAt,  DateTime updatedAt,  List<String> myRoles,  CompanyCounts counts)?  $default,) {final _that = this;
switch (_that) {
case _AdminCompany() when $default != null:
return $default(_that.id,_that.name,_that.taxId,_that.prefix,_that.status,_that.isKscEntity,_that.defaultApproverId,_that.createdAt,_that.updatedAt,_that.myRoles,_that.counts);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _AdminCompany extends AdminCompany {
  const _AdminCompany({required this.id, required this.name, this.taxId, required this.prefix, required this.status, this.isKscEntity = false, this.defaultApproverId, required this.createdAt, required this.updatedAt,  List<String> myRoles = const <String>[], this.counts = const CompanyCounts()}): _myRoles = myRoles,super._();
  factory _AdminCompany.fromJson(Map<String, dynamic> json) => _$AdminCompanyFromJson(json);

@override final  String id;
@override final  String name;
@override final  String? taxId;
@override final  String prefix;
@override final  String status;
@override@JsonKey() final  bool isKscEntity;
@override final  String? defaultApproverId;
@override final  DateTime createdAt;
@override final  DateTime updatedAt;
 final  List<String> _myRoles;
@override@JsonKey() List<String> get myRoles {
  if (_myRoles is EqualUnmodifiableListView) return _myRoles;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_myRoles);
}

@override@JsonKey() final  CompanyCounts counts;

/// Create a copy of AdminCompany
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AdminCompanyCopyWith<_AdminCompany> get copyWith => __$AdminCompanyCopyWithImpl<_AdminCompany>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$AdminCompanyToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _AdminCompany&&(identical(other.id, id) || other.id == id)&&(identical(other.name, name) || other.name == name)&&(identical(other.taxId, taxId) || other.taxId == taxId)&&(identical(other.prefix, prefix) || other.prefix == prefix)&&(identical(other.status, status) || other.status == status)&&(identical(other.isKscEntity, isKscEntity) || other.isKscEntity == isKscEntity)&&(identical(other.defaultApproverId, defaultApproverId) || other.defaultApproverId == defaultApproverId)&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt)&&(identical(other.updatedAt, updatedAt) || other.updatedAt == updatedAt)&&const DeepCollectionEquality().equals(other.myRoles, _myRoles)&&(identical(other.counts, counts) || other.counts == counts));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,name,taxId,prefix,status,isKscEntity,defaultApproverId,createdAt,updatedAt,const DeepCollectionEquality().hash(_myRoles),counts);
}

@override
String toString() {
    return 'AdminCompany(id: $id, name: $name, taxId: $taxId, prefix: $prefix, status: $status, isKscEntity: $isKscEntity, defaultApproverId: $defaultApproverId, createdAt: $createdAt, updatedAt: $updatedAt, myRoles: $myRoles, counts: $counts)';
}


}

/// @nodoc
abstract mixin class _$AdminCompanyCopyWith<$Res> implements $AdminCompanyCopyWith<$Res> {
  factory _$AdminCompanyCopyWith(_AdminCompany value, $Res Function(_AdminCompany) _then) = __$AdminCompanyCopyWithImpl;
@override @useResult
$Res call({
 String id, String name, String? taxId, String prefix, String status, bool isKscEntity, String? defaultApproverId, DateTime createdAt, DateTime updatedAt, List<String> myRoles, CompanyCounts counts
});


@override $CompanyCountsCopyWith<$Res> get counts;

}
/// @nodoc
class __$AdminCompanyCopyWithImpl<$Res>
    implements _$AdminCompanyCopyWith<$Res> {
  __$AdminCompanyCopyWithImpl(this._self, this._then);

  final _AdminCompany _self;
  final $Res Function(_AdminCompany) _then;

/// Create a copy of AdminCompany
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? name = null,Object? taxId = freezed,Object? prefix = null,Object? status = null,Object? isKscEntity = null,Object? defaultApproverId = freezed,Object? createdAt = null,Object? updatedAt = null,Object? myRoles = null,Object? counts = null,}) {
  return _then(_AdminCompany(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,taxId: freezed == taxId ? _self.taxId : taxId // ignore: cast_nullable_to_non_nullable
as String?,prefix: null == prefix ? _self.prefix : prefix // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,isKscEntity: null == isKscEntity ? _self.isKscEntity : isKscEntity // ignore: cast_nullable_to_non_nullable
as bool,defaultApproverId: freezed == defaultApproverId ? _self.defaultApproverId : defaultApproverId // ignore: cast_nullable_to_non_nullable
as String?,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,updatedAt: null == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime,myRoles: null == myRoles ? _self._myRoles : myRoles // ignore: cast_nullable_to_non_nullable
as List<String>,counts: null == counts ? _self.counts : counts // ignore: cast_nullable_to_non_nullable
as CompanyCounts,
  ));
}

/// Create a copy of AdminCompany
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$CompanyCountsCopyWith<$Res> get counts {
  
  return $CompanyCountsCopyWith<$Res>(_self.counts, (value) {
    return _then(_self.copyWith(counts: value));
  });
}
}


/// @nodoc
mixin _$UserAccount {

 String get id; String get externalId; String get email; String get displayName; bool get isAppAdmin; bool get isActive; DateTime? get createdAt; DateTime? get updatedAt; bool get hasPassword; bool get mustChangePassword; DateTime? get passwordChangedAt; DateTime? get lockedUntil; DateTime? get tempPasswordExpiresAt;
/// Create a copy of UserAccount
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$UserAccountCopyWith<UserAccount> get copyWith => _$UserAccountCopyWithImpl<UserAccount>(this as UserAccount, _$identity);

  /// Serializes this UserAccount to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as UserAccount;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is UserAccount&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.externalId, _this.externalId) || other.externalId == _this.externalId)&&(identical(other.email, _this.email) || other.email == _this.email)&&(identical(other.displayName, _this.displayName) || other.displayName == _this.displayName)&&(identical(other.isAppAdmin, _this.isAppAdmin) || other.isAppAdmin == _this.isAppAdmin)&&(identical(other.isActive, _this.isActive) || other.isActive == _this.isActive)&&(identical(other.createdAt, _this.createdAt) || other.createdAt == _this.createdAt)&&(identical(other.updatedAt, _this.updatedAt) || other.updatedAt == _this.updatedAt)&&(identical(other.hasPassword, _this.hasPassword) || other.hasPassword == _this.hasPassword)&&(identical(other.mustChangePassword, _this.mustChangePassword) || other.mustChangePassword == _this.mustChangePassword)&&(identical(other.passwordChangedAt, _this.passwordChangedAt) || other.passwordChangedAt == _this.passwordChangedAt)&&(identical(other.lockedUntil, _this.lockedUntil) || other.lockedUntil == _this.lockedUntil)&&(identical(other.tempPasswordExpiresAt, _this.tempPasswordExpiresAt) || other.tempPasswordExpiresAt == _this.tempPasswordExpiresAt));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as UserAccount;
  return Object.hash(runtimeType,_this.id,_this.externalId,_this.email,_this.displayName,_this.isAppAdmin,_this.isActive,_this.createdAt,_this.updatedAt,_this.hasPassword,_this.mustChangePassword,_this.passwordChangedAt,_this.lockedUntil,_this.tempPasswordExpiresAt);
}

@override
String toString() {
  final _this = this as UserAccount;
  return 'UserAccount(id: ${_this.id}, externalId: ${_this.externalId}, email: ${_this.email}, displayName: ${_this.displayName}, isAppAdmin: ${_this.isAppAdmin}, isActive: ${_this.isActive}, createdAt: ${_this.createdAt}, updatedAt: ${_this.updatedAt}, hasPassword: ${_this.hasPassword}, mustChangePassword: ${_this.mustChangePassword}, passwordChangedAt: ${_this.passwordChangedAt}, lockedUntil: ${_this.lockedUntil}, tempPasswordExpiresAt: ${_this.tempPasswordExpiresAt})';
}


}

/// @nodoc
abstract mixin class $UserAccountCopyWith<$Res>  {
  factory $UserAccountCopyWith(UserAccount value, $Res Function(UserAccount) _then) = _$UserAccountCopyWithImpl;
@useResult
$Res call({
 String id, String externalId, String email, String displayName, bool isAppAdmin, bool isActive, DateTime? createdAt, DateTime? updatedAt, bool hasPassword, bool mustChangePassword, DateTime? passwordChangedAt, DateTime? lockedUntil, DateTime? tempPasswordExpiresAt
});




}
/// @nodoc
class _$UserAccountCopyWithImpl<$Res>
    implements $UserAccountCopyWith<$Res> {
  _$UserAccountCopyWithImpl(this._self, this._then);

  final UserAccount _self;
  final $Res Function(UserAccount) _then;

/// Create a copy of UserAccount
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? externalId = null,Object? email = null,Object? displayName = null,Object? isAppAdmin = null,Object? isActive = null,Object? createdAt = freezed,Object? updatedAt = freezed,Object? hasPassword = null,Object? mustChangePassword = null,Object? passwordChangedAt = freezed,Object? lockedUntil = freezed,Object? tempPasswordExpiresAt = freezed,}) {
  return _then(UserAccount(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,externalId: null == externalId ? _self.externalId : externalId // ignore: cast_nullable_to_non_nullable
as String,email: null == email ? _self.email : email // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,isAppAdmin: null == isAppAdmin ? _self.isAppAdmin : isAppAdmin // ignore: cast_nullable_to_non_nullable
as bool,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,createdAt: freezed == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime?,updatedAt: freezed == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,hasPassword: null == hasPassword ? _self.hasPassword : hasPassword // ignore: cast_nullable_to_non_nullable
as bool,mustChangePassword: null == mustChangePassword ? _self.mustChangePassword : mustChangePassword // ignore: cast_nullable_to_non_nullable
as bool,passwordChangedAt: freezed == passwordChangedAt ? _self.passwordChangedAt : passwordChangedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,lockedUntil: freezed == lockedUntil ? _self.lockedUntil : lockedUntil // ignore: cast_nullable_to_non_nullable
as DateTime?,tempPasswordExpiresAt: freezed == tempPasswordExpiresAt ? _self.tempPasswordExpiresAt : tempPasswordExpiresAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}

}


/// Adds pattern-matching-related methods to [UserAccount].
extension UserAccountPatterns on UserAccount {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _UserAccount value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _UserAccount() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _UserAccount value)  $default,){
final _that = this;
switch (_that) {
case _UserAccount():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _UserAccount value)?  $default,){
final _that = this;
switch (_that) {
case _UserAccount() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String externalId,  String email,  String displayName,  bool isAppAdmin,  bool isActive,  DateTime? createdAt,  DateTime? updatedAt,  bool hasPassword,  bool mustChangePassword,  DateTime? passwordChangedAt,  DateTime? lockedUntil,  DateTime? tempPasswordExpiresAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _UserAccount() when $default != null:
return $default(_that.id,_that.externalId,_that.email,_that.displayName,_that.isAppAdmin,_that.isActive,_that.createdAt,_that.updatedAt,_that.hasPassword,_that.mustChangePassword,_that.passwordChangedAt,_that.lockedUntil,_that.tempPasswordExpiresAt);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String externalId,  String email,  String displayName,  bool isAppAdmin,  bool isActive,  DateTime? createdAt,  DateTime? updatedAt,  bool hasPassword,  bool mustChangePassword,  DateTime? passwordChangedAt,  DateTime? lockedUntil,  DateTime? tempPasswordExpiresAt)  $default,) {final _that = this;
switch (_that) {
case _UserAccount():
return $default(_that.id,_that.externalId,_that.email,_that.displayName,_that.isAppAdmin,_that.isActive,_that.createdAt,_that.updatedAt,_that.hasPassword,_that.mustChangePassword,_that.passwordChangedAt,_that.lockedUntil,_that.tempPasswordExpiresAt);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String externalId,  String email,  String displayName,  bool isAppAdmin,  bool isActive,  DateTime? createdAt,  DateTime? updatedAt,  bool hasPassword,  bool mustChangePassword,  DateTime? passwordChangedAt,  DateTime? lockedUntil,  DateTime? tempPasswordExpiresAt)?  $default,) {final _that = this;
switch (_that) {
case _UserAccount() when $default != null:
return $default(_that.id,_that.externalId,_that.email,_that.displayName,_that.isAppAdmin,_that.isActive,_that.createdAt,_that.updatedAt,_that.hasPassword,_that.mustChangePassword,_that.passwordChangedAt,_that.lockedUntil,_that.tempPasswordExpiresAt);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _UserAccount implements UserAccount {
  const _UserAccount({required this.id, this.externalId = '', this.email = '', required this.displayName, this.isAppAdmin = false, required this.isActive, this.createdAt, this.updatedAt, this.hasPassword = false, this.mustChangePassword = false, this.passwordChangedAt, this.lockedUntil, this.tempPasswordExpiresAt});
  factory _UserAccount.fromJson(Map<String, dynamic> json) => _$UserAccountFromJson(json);

@override final  String id;
@override@JsonKey() final  String externalId;
@override@JsonKey() final  String email;
@override final  String displayName;
@override@JsonKey() final  bool isAppAdmin;
@override final  bool isActive;
@override final  DateTime? createdAt;
@override final  DateTime? updatedAt;
@override@JsonKey() final  bool hasPassword;
@override@JsonKey() final  bool mustChangePassword;
@override final  DateTime? passwordChangedAt;
@override final  DateTime? lockedUntil;
@override final  DateTime? tempPasswordExpiresAt;

/// Create a copy of UserAccount
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$UserAccountCopyWith<_UserAccount> get copyWith => __$UserAccountCopyWithImpl<_UserAccount>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$UserAccountToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _UserAccount&&(identical(other.id, id) || other.id == id)&&(identical(other.externalId, externalId) || other.externalId == externalId)&&(identical(other.email, email) || other.email == email)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.isAppAdmin, isAppAdmin) || other.isAppAdmin == isAppAdmin)&&(identical(other.isActive, isActive) || other.isActive == isActive)&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt)&&(identical(other.updatedAt, updatedAt) || other.updatedAt == updatedAt)&&(identical(other.hasPassword, hasPassword) || other.hasPassword == hasPassword)&&(identical(other.mustChangePassword, mustChangePassword) || other.mustChangePassword == mustChangePassword)&&(identical(other.passwordChangedAt, passwordChangedAt) || other.passwordChangedAt == passwordChangedAt)&&(identical(other.lockedUntil, lockedUntil) || other.lockedUntil == lockedUntil)&&(identical(other.tempPasswordExpiresAt, tempPasswordExpiresAt) || other.tempPasswordExpiresAt == tempPasswordExpiresAt));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,externalId,email,displayName,isAppAdmin,isActive,createdAt,updatedAt,hasPassword,mustChangePassword,passwordChangedAt,lockedUntil,tempPasswordExpiresAt);
}

@override
String toString() {
    return 'UserAccount(id: $id, externalId: $externalId, email: $email, displayName: $displayName, isAppAdmin: $isAppAdmin, isActive: $isActive, createdAt: $createdAt, updatedAt: $updatedAt, hasPassword: $hasPassword, mustChangePassword: $mustChangePassword, passwordChangedAt: $passwordChangedAt, lockedUntil: $lockedUntil, tempPasswordExpiresAt: $tempPasswordExpiresAt)';
}


}

/// @nodoc
abstract mixin class _$UserAccountCopyWith<$Res> implements $UserAccountCopyWith<$Res> {
  factory _$UserAccountCopyWith(_UserAccount value, $Res Function(_UserAccount) _then) = __$UserAccountCopyWithImpl;
@override @useResult
$Res call({
 String id, String externalId, String email, String displayName, bool isAppAdmin, bool isActive, DateTime? createdAt, DateTime? updatedAt, bool hasPassword, bool mustChangePassword, DateTime? passwordChangedAt, DateTime? lockedUntil, DateTime? tempPasswordExpiresAt
});




}
/// @nodoc
class __$UserAccountCopyWithImpl<$Res>
    implements _$UserAccountCopyWith<$Res> {
  __$UserAccountCopyWithImpl(this._self, this._then);

  final _UserAccount _self;
  final $Res Function(_UserAccount) _then;

/// Create a copy of UserAccount
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? externalId = null,Object? email = null,Object? displayName = null,Object? isAppAdmin = null,Object? isActive = null,Object? createdAt = freezed,Object? updatedAt = freezed,Object? hasPassword = null,Object? mustChangePassword = null,Object? passwordChangedAt = freezed,Object? lockedUntil = freezed,Object? tempPasswordExpiresAt = freezed,}) {
  return _then(_UserAccount(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,externalId: null == externalId ? _self.externalId : externalId // ignore: cast_nullable_to_non_nullable
as String,email: null == email ? _self.email : email // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,isAppAdmin: null == isAppAdmin ? _self.isAppAdmin : isAppAdmin // ignore: cast_nullable_to_non_nullable
as bool,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,createdAt: freezed == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime?,updatedAt: freezed == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,hasPassword: null == hasPassword ? _self.hasPassword : hasPassword // ignore: cast_nullable_to_non_nullable
as bool,mustChangePassword: null == mustChangePassword ? _self.mustChangePassword : mustChangePassword // ignore: cast_nullable_to_non_nullable
as bool,passwordChangedAt: freezed == passwordChangedAt ? _self.passwordChangedAt : passwordChangedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,lockedUntil: freezed == lockedUntil ? _self.lockedUntil : lockedUntil // ignore: cast_nullable_to_non_nullable
as DateTime?,tempPasswordExpiresAt: freezed == tempPasswordExpiresAt ? _self.tempPasswordExpiresAt : tempPasswordExpiresAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}


}


/// @nodoc
mixin _$UserWithTemporaryPassword {

 UserAccount get user; String get temporaryPassword;
/// Create a copy of UserWithTemporaryPassword
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$UserWithTemporaryPasswordCopyWith<UserWithTemporaryPassword> get copyWith => _$UserWithTemporaryPasswordCopyWithImpl<UserWithTemporaryPassword>(this as UserWithTemporaryPassword, _$identity);

  /// Serializes this UserWithTemporaryPassword to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as UserWithTemporaryPassword;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is UserWithTemporaryPassword&&(identical(other.user, _this.user) || other.user == _this.user)&&(identical(other.temporaryPassword, _this.temporaryPassword) || other.temporaryPassword == _this.temporaryPassword));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as UserWithTemporaryPassword;
  return Object.hash(runtimeType,_this.user,_this.temporaryPassword);
}

@override
String toString() {
  final _this = this as UserWithTemporaryPassword;
  return 'UserWithTemporaryPassword(user: ${_this.user}, temporaryPassword: ${_this.temporaryPassword})';
}


}

/// @nodoc
abstract mixin class $UserWithTemporaryPasswordCopyWith<$Res>  {
  factory $UserWithTemporaryPasswordCopyWith(UserWithTemporaryPassword value, $Res Function(UserWithTemporaryPassword) _then) = _$UserWithTemporaryPasswordCopyWithImpl;
@useResult
$Res call({
 UserAccount user, String temporaryPassword
});


$UserAccountCopyWith<$Res> get user;

}
/// @nodoc
class _$UserWithTemporaryPasswordCopyWithImpl<$Res>
    implements $UserWithTemporaryPasswordCopyWith<$Res> {
  _$UserWithTemporaryPasswordCopyWithImpl(this._self, this._then);

  final UserWithTemporaryPassword _self;
  final $Res Function(UserWithTemporaryPassword) _then;

/// Create a copy of UserWithTemporaryPassword
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? user = null,Object? temporaryPassword = null,}) {
  return _then(UserWithTemporaryPassword(
user: null == user ? _self.user : user // ignore: cast_nullable_to_non_nullable
as UserAccount,temporaryPassword: null == temporaryPassword ? _self.temporaryPassword : temporaryPassword // ignore: cast_nullable_to_non_nullable
as String,
  ));
}
/// Create a copy of UserWithTemporaryPassword
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserAccountCopyWith<$Res> get user {
  
  return $UserAccountCopyWith<$Res>(_self.user, (value) {
    return _then(_self.copyWith(user: value));
  });
}
}


/// Adds pattern-matching-related methods to [UserWithTemporaryPassword].
extension UserWithTemporaryPasswordPatterns on UserWithTemporaryPassword {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _UserWithTemporaryPassword value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _UserWithTemporaryPassword() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _UserWithTemporaryPassword value)  $default,){
final _that = this;
switch (_that) {
case _UserWithTemporaryPassword():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _UserWithTemporaryPassword value)?  $default,){
final _that = this;
switch (_that) {
case _UserWithTemporaryPassword() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( UserAccount user,  String temporaryPassword)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _UserWithTemporaryPassword() when $default != null:
return $default(_that.user,_that.temporaryPassword);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( UserAccount user,  String temporaryPassword)  $default,) {final _that = this;
switch (_that) {
case _UserWithTemporaryPassword():
return $default(_that.user,_that.temporaryPassword);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( UserAccount user,  String temporaryPassword)?  $default,) {final _that = this;
switch (_that) {
case _UserWithTemporaryPassword() when $default != null:
return $default(_that.user,_that.temporaryPassword);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _UserWithTemporaryPassword implements UserWithTemporaryPassword {
  const _UserWithTemporaryPassword({required this.user, required this.temporaryPassword});
  factory _UserWithTemporaryPassword.fromJson(Map<String, dynamic> json) => _$UserWithTemporaryPasswordFromJson(json);

@override final  UserAccount user;
@override final  String temporaryPassword;

/// Create a copy of UserWithTemporaryPassword
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$UserWithTemporaryPasswordCopyWith<_UserWithTemporaryPassword> get copyWith => __$UserWithTemporaryPasswordCopyWithImpl<_UserWithTemporaryPassword>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$UserWithTemporaryPasswordToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _UserWithTemporaryPassword&&(identical(other.user, user) || other.user == user)&&(identical(other.temporaryPassword, temporaryPassword) || other.temporaryPassword == temporaryPassword));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,user,temporaryPassword);
}

@override
String toString() {
    return 'UserWithTemporaryPassword(user: $user, temporaryPassword: $temporaryPassword)';
}


}

/// @nodoc
abstract mixin class _$UserWithTemporaryPasswordCopyWith<$Res> implements $UserWithTemporaryPasswordCopyWith<$Res> {
  factory _$UserWithTemporaryPasswordCopyWith(_UserWithTemporaryPassword value, $Res Function(_UserWithTemporaryPassword) _then) = __$UserWithTemporaryPasswordCopyWithImpl;
@override @useResult
$Res call({
 UserAccount user, String temporaryPassword
});


@override $UserAccountCopyWith<$Res> get user;

}
/// @nodoc
class __$UserWithTemporaryPasswordCopyWithImpl<$Res>
    implements _$UserWithTemporaryPasswordCopyWith<$Res> {
  __$UserWithTemporaryPasswordCopyWithImpl(this._self, this._then);

  final _UserWithTemporaryPassword _self;
  final $Res Function(_UserWithTemporaryPassword) _then;

/// Create a copy of UserWithTemporaryPassword
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? user = null,Object? temporaryPassword = null,}) {
  return _then(_UserWithTemporaryPassword(
user: null == user ? _self.user : user // ignore: cast_nullable_to_non_nullable
as UserAccount,temporaryPassword: null == temporaryPassword ? _self.temporaryPassword : temporaryPassword // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

/// Create a copy of UserWithTemporaryPassword
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserAccountCopyWith<$Res> get user {
  
  return $UserAccountCopyWith<$Res>(_self.user, (value) {
    return _then(_self.copyWith(user: value));
  });
}
}


/// @nodoc
mixin _$UserMembership {

 String get companyId; String get companyName; String get companyPrefix; String get companyStatus; List<String> get roles;
/// Create a copy of UserMembership
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$UserMembershipCopyWith<UserMembership> get copyWith => _$UserMembershipCopyWithImpl<UserMembership>(this as UserMembership, _$identity);

  /// Serializes this UserMembership to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as UserMembership;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is UserMembership&&(identical(other.companyId, _this.companyId) || other.companyId == _this.companyId)&&(identical(other.companyName, _this.companyName) || other.companyName == _this.companyName)&&(identical(other.companyPrefix, _this.companyPrefix) || other.companyPrefix == _this.companyPrefix)&&(identical(other.companyStatus, _this.companyStatus) || other.companyStatus == _this.companyStatus)&&const DeepCollectionEquality().equals(other.roles, _this.roles));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as UserMembership;
  return Object.hash(runtimeType,_this.companyId,_this.companyName,_this.companyPrefix,_this.companyStatus,const DeepCollectionEquality().hash(_this.roles));
}

@override
String toString() {
  final _this = this as UserMembership;
  return 'UserMembership(companyId: ${_this.companyId}, companyName: ${_this.companyName}, companyPrefix: ${_this.companyPrefix}, companyStatus: ${_this.companyStatus}, roles: ${_this.roles})';
}


}

/// @nodoc
abstract mixin class $UserMembershipCopyWith<$Res>  {
  factory $UserMembershipCopyWith(UserMembership value, $Res Function(UserMembership) _then) = _$UserMembershipCopyWithImpl;
@useResult
$Res call({
 String companyId, String companyName, String companyPrefix, String companyStatus, List<String> roles
});




}
/// @nodoc
class _$UserMembershipCopyWithImpl<$Res>
    implements $UserMembershipCopyWith<$Res> {
  _$UserMembershipCopyWithImpl(this._self, this._then);

  final UserMembership _self;
  final $Res Function(UserMembership) _then;

/// Create a copy of UserMembership
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? companyId = null,Object? companyName = null,Object? companyPrefix = null,Object? companyStatus = null,Object? roles = null,}) {
  return _then(UserMembership(
companyId: null == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String,companyName: null == companyName ? _self.companyName : companyName // ignore: cast_nullable_to_non_nullable
as String,companyPrefix: null == companyPrefix ? _self.companyPrefix : companyPrefix // ignore: cast_nullable_to_non_nullable
as String,companyStatus: null == companyStatus ? _self.companyStatus : companyStatus // ignore: cast_nullable_to_non_nullable
as String,roles: null == roles ? _self.roles : roles // ignore: cast_nullable_to_non_nullable
as List<String>,
  ));
}

}


/// Adds pattern-matching-related methods to [UserMembership].
extension UserMembershipPatterns on UserMembership {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _UserMembership value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _UserMembership() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _UserMembership value)  $default,){
final _that = this;
switch (_that) {
case _UserMembership():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _UserMembership value)?  $default,){
final _that = this;
switch (_that) {
case _UserMembership() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String companyId,  String companyName,  String companyPrefix,  String companyStatus,  List<String> roles)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _UserMembership() when $default != null:
return $default(_that.companyId,_that.companyName,_that.companyPrefix,_that.companyStatus,_that.roles);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String companyId,  String companyName,  String companyPrefix,  String companyStatus,  List<String> roles)  $default,) {final _that = this;
switch (_that) {
case _UserMembership():
return $default(_that.companyId,_that.companyName,_that.companyPrefix,_that.companyStatus,_that.roles);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String companyId,  String companyName,  String companyPrefix,  String companyStatus,  List<String> roles)?  $default,) {final _that = this;
switch (_that) {
case _UserMembership() when $default != null:
return $default(_that.companyId,_that.companyName,_that.companyPrefix,_that.companyStatus,_that.roles);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _UserMembership extends UserMembership {
  const _UserMembership({required this.companyId, required this.companyName, required this.companyPrefix, this.companyStatus = 'active',  List<String> roles = const <String>[]}): _roles = roles,super._();
  factory _UserMembership.fromJson(Map<String, dynamic> json) => _$UserMembershipFromJson(json);

@override final  String companyId;
@override final  String companyName;
@override final  String companyPrefix;
@override@JsonKey() final  String companyStatus;
 final  List<String> _roles;
@override@JsonKey() List<String> get roles {
  if (_roles is EqualUnmodifiableListView) return _roles;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_roles);
}


/// Create a copy of UserMembership
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$UserMembershipCopyWith<_UserMembership> get copyWith => __$UserMembershipCopyWithImpl<_UserMembership>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$UserMembershipToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _UserMembership&&(identical(other.companyId, companyId) || other.companyId == companyId)&&(identical(other.companyName, companyName) || other.companyName == companyName)&&(identical(other.companyPrefix, companyPrefix) || other.companyPrefix == companyPrefix)&&(identical(other.companyStatus, companyStatus) || other.companyStatus == companyStatus)&&const DeepCollectionEquality().equals(other.roles, _roles));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,companyId,companyName,companyPrefix,companyStatus,const DeepCollectionEquality().hash(_roles));
}

@override
String toString() {
    return 'UserMembership(companyId: $companyId, companyName: $companyName, companyPrefix: $companyPrefix, companyStatus: $companyStatus, roles: $roles)';
}


}

/// @nodoc
abstract mixin class _$UserMembershipCopyWith<$Res> implements $UserMembershipCopyWith<$Res> {
  factory _$UserMembershipCopyWith(_UserMembership value, $Res Function(_UserMembership) _then) = __$UserMembershipCopyWithImpl;
@override @useResult
$Res call({
 String companyId, String companyName, String companyPrefix, String companyStatus, List<String> roles
});




}
/// @nodoc
class __$UserMembershipCopyWithImpl<$Res>
    implements _$UserMembershipCopyWith<$Res> {
  __$UserMembershipCopyWithImpl(this._self, this._then);

  final _UserMembership _self;
  final $Res Function(_UserMembership) _then;

/// Create a copy of UserMembership
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? companyId = null,Object? companyName = null,Object? companyPrefix = null,Object? companyStatus = null,Object? roles = null,}) {
  return _then(_UserMembership(
companyId: null == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String,companyName: null == companyName ? _self.companyName : companyName // ignore: cast_nullable_to_non_nullable
as String,companyPrefix: null == companyPrefix ? _self.companyPrefix : companyPrefix // ignore: cast_nullable_to_non_nullable
as String,companyStatus: null == companyStatus ? _self.companyStatus : companyStatus // ignore: cast_nullable_to_non_nullable
as String,roles: null == roles ? _self._roles : roles // ignore: cast_nullable_to_non_nullable
as List<String>,
  ));
}


}


/// @nodoc
mixin _$UserDetail {

 String get id; String get externalId; String get email; String get displayName; bool get isAppAdmin; bool get isActive; bool get hasPassword; bool get mustChangePassword; DateTime? get passwordChangedAt; DateTime? get lockedUntil; DateTime? get tempPasswordExpiresAt; List<UserMembership> get memberships;
/// Create a copy of UserDetail
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$UserDetailCopyWith<UserDetail> get copyWith => _$UserDetailCopyWithImpl<UserDetail>(this as UserDetail, _$identity);

  /// Serializes this UserDetail to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as UserDetail;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is UserDetail&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.externalId, _this.externalId) || other.externalId == _this.externalId)&&(identical(other.email, _this.email) || other.email == _this.email)&&(identical(other.displayName, _this.displayName) || other.displayName == _this.displayName)&&(identical(other.isAppAdmin, _this.isAppAdmin) || other.isAppAdmin == _this.isAppAdmin)&&(identical(other.isActive, _this.isActive) || other.isActive == _this.isActive)&&(identical(other.hasPassword, _this.hasPassword) || other.hasPassword == _this.hasPassword)&&(identical(other.mustChangePassword, _this.mustChangePassword) || other.mustChangePassword == _this.mustChangePassword)&&(identical(other.passwordChangedAt, _this.passwordChangedAt) || other.passwordChangedAt == _this.passwordChangedAt)&&(identical(other.lockedUntil, _this.lockedUntil) || other.lockedUntil == _this.lockedUntil)&&(identical(other.tempPasswordExpiresAt, _this.tempPasswordExpiresAt) || other.tempPasswordExpiresAt == _this.tempPasswordExpiresAt)&&const DeepCollectionEquality().equals(other.memberships, _this.memberships));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as UserDetail;
  return Object.hash(runtimeType,_this.id,_this.externalId,_this.email,_this.displayName,_this.isAppAdmin,_this.isActive,_this.hasPassword,_this.mustChangePassword,_this.passwordChangedAt,_this.lockedUntil,_this.tempPasswordExpiresAt,const DeepCollectionEquality().hash(_this.memberships));
}

@override
String toString() {
  final _this = this as UserDetail;
  return 'UserDetail(id: ${_this.id}, externalId: ${_this.externalId}, email: ${_this.email}, displayName: ${_this.displayName}, isAppAdmin: ${_this.isAppAdmin}, isActive: ${_this.isActive}, hasPassword: ${_this.hasPassword}, mustChangePassword: ${_this.mustChangePassword}, passwordChangedAt: ${_this.passwordChangedAt}, lockedUntil: ${_this.lockedUntil}, tempPasswordExpiresAt: ${_this.tempPasswordExpiresAt}, memberships: ${_this.memberships})';
}


}

/// @nodoc
abstract mixin class $UserDetailCopyWith<$Res>  {
  factory $UserDetailCopyWith(UserDetail value, $Res Function(UserDetail) _then) = _$UserDetailCopyWithImpl;
@useResult
$Res call({
 String id, String externalId, String email, String displayName, bool isAppAdmin, bool isActive, bool hasPassword, bool mustChangePassword, DateTime? passwordChangedAt, DateTime? lockedUntil, DateTime? tempPasswordExpiresAt, List<UserMembership> memberships
});




}
/// @nodoc
class _$UserDetailCopyWithImpl<$Res>
    implements $UserDetailCopyWith<$Res> {
  _$UserDetailCopyWithImpl(this._self, this._then);

  final UserDetail _self;
  final $Res Function(UserDetail) _then;

/// Create a copy of UserDetail
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? externalId = null,Object? email = null,Object? displayName = null,Object? isAppAdmin = null,Object? isActive = null,Object? hasPassword = null,Object? mustChangePassword = null,Object? passwordChangedAt = freezed,Object? lockedUntil = freezed,Object? tempPasswordExpiresAt = freezed,Object? memberships = null,}) {
  return _then(UserDetail(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,externalId: null == externalId ? _self.externalId : externalId // ignore: cast_nullable_to_non_nullable
as String,email: null == email ? _self.email : email // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,isAppAdmin: null == isAppAdmin ? _self.isAppAdmin : isAppAdmin // ignore: cast_nullable_to_non_nullable
as bool,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,hasPassword: null == hasPassword ? _self.hasPassword : hasPassword // ignore: cast_nullable_to_non_nullable
as bool,mustChangePassword: null == mustChangePassword ? _self.mustChangePassword : mustChangePassword // ignore: cast_nullable_to_non_nullable
as bool,passwordChangedAt: freezed == passwordChangedAt ? _self.passwordChangedAt : passwordChangedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,lockedUntil: freezed == lockedUntil ? _self.lockedUntil : lockedUntil // ignore: cast_nullable_to_non_nullable
as DateTime?,tempPasswordExpiresAt: freezed == tempPasswordExpiresAt ? _self.tempPasswordExpiresAt : tempPasswordExpiresAt // ignore: cast_nullable_to_non_nullable
as DateTime?,memberships: null == memberships ? _self.memberships : memberships // ignore: cast_nullable_to_non_nullable
as List<UserMembership>,
  ));
}

}


/// Adds pattern-matching-related methods to [UserDetail].
extension UserDetailPatterns on UserDetail {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _UserDetail value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _UserDetail() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _UserDetail value)  $default,){
final _that = this;
switch (_that) {
case _UserDetail():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _UserDetail value)?  $default,){
final _that = this;
switch (_that) {
case _UserDetail() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String externalId,  String email,  String displayName,  bool isAppAdmin,  bool isActive,  bool hasPassword,  bool mustChangePassword,  DateTime? passwordChangedAt,  DateTime? lockedUntil,  DateTime? tempPasswordExpiresAt,  List<UserMembership> memberships)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _UserDetail() when $default != null:
return $default(_that.id,_that.externalId,_that.email,_that.displayName,_that.isAppAdmin,_that.isActive,_that.hasPassword,_that.mustChangePassword,_that.passwordChangedAt,_that.lockedUntil,_that.tempPasswordExpiresAt,_that.memberships);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String externalId,  String email,  String displayName,  bool isAppAdmin,  bool isActive,  bool hasPassword,  bool mustChangePassword,  DateTime? passwordChangedAt,  DateTime? lockedUntil,  DateTime? tempPasswordExpiresAt,  List<UserMembership> memberships)  $default,) {final _that = this;
switch (_that) {
case _UserDetail():
return $default(_that.id,_that.externalId,_that.email,_that.displayName,_that.isAppAdmin,_that.isActive,_that.hasPassword,_that.mustChangePassword,_that.passwordChangedAt,_that.lockedUntil,_that.tempPasswordExpiresAt,_that.memberships);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String externalId,  String email,  String displayName,  bool isAppAdmin,  bool isActive,  bool hasPassword,  bool mustChangePassword,  DateTime? passwordChangedAt,  DateTime? lockedUntil,  DateTime? tempPasswordExpiresAt,  List<UserMembership> memberships)?  $default,) {final _that = this;
switch (_that) {
case _UserDetail() when $default != null:
return $default(_that.id,_that.externalId,_that.email,_that.displayName,_that.isAppAdmin,_that.isActive,_that.hasPassword,_that.mustChangePassword,_that.passwordChangedAt,_that.lockedUntil,_that.tempPasswordExpiresAt,_that.memberships);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _UserDetail implements UserDetail {
  const _UserDetail({required this.id, this.externalId = '', this.email = '', required this.displayName, this.isAppAdmin = false, required this.isActive, this.hasPassword = false, this.mustChangePassword = false, this.passwordChangedAt, this.lockedUntil, this.tempPasswordExpiresAt,  List<UserMembership> memberships = const <UserMembership>[]}): _memberships = memberships;
  factory _UserDetail.fromJson(Map<String, dynamic> json) => _$UserDetailFromJson(json);

@override final  String id;
@override@JsonKey() final  String externalId;
@override@JsonKey() final  String email;
@override final  String displayName;
@override@JsonKey() final  bool isAppAdmin;
@override final  bool isActive;
@override@JsonKey() final  bool hasPassword;
@override@JsonKey() final  bool mustChangePassword;
@override final  DateTime? passwordChangedAt;
@override final  DateTime? lockedUntil;
@override final  DateTime? tempPasswordExpiresAt;
 final  List<UserMembership> _memberships;
@override@JsonKey() List<UserMembership> get memberships {
  if (_memberships is EqualUnmodifiableListView) return _memberships;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_memberships);
}


/// Create a copy of UserDetail
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$UserDetailCopyWith<_UserDetail> get copyWith => __$UserDetailCopyWithImpl<_UserDetail>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$UserDetailToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _UserDetail&&(identical(other.id, id) || other.id == id)&&(identical(other.externalId, externalId) || other.externalId == externalId)&&(identical(other.email, email) || other.email == email)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.isAppAdmin, isAppAdmin) || other.isAppAdmin == isAppAdmin)&&(identical(other.isActive, isActive) || other.isActive == isActive)&&(identical(other.hasPassword, hasPassword) || other.hasPassword == hasPassword)&&(identical(other.mustChangePassword, mustChangePassword) || other.mustChangePassword == mustChangePassword)&&(identical(other.passwordChangedAt, passwordChangedAt) || other.passwordChangedAt == passwordChangedAt)&&(identical(other.lockedUntil, lockedUntil) || other.lockedUntil == lockedUntil)&&(identical(other.tempPasswordExpiresAt, tempPasswordExpiresAt) || other.tempPasswordExpiresAt == tempPasswordExpiresAt)&&const DeepCollectionEquality().equals(other.memberships, _memberships));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,externalId,email,displayName,isAppAdmin,isActive,hasPassword,mustChangePassword,passwordChangedAt,lockedUntil,tempPasswordExpiresAt,const DeepCollectionEquality().hash(_memberships));
}

@override
String toString() {
    return 'UserDetail(id: $id, externalId: $externalId, email: $email, displayName: $displayName, isAppAdmin: $isAppAdmin, isActive: $isActive, hasPassword: $hasPassword, mustChangePassword: $mustChangePassword, passwordChangedAt: $passwordChangedAt, lockedUntil: $lockedUntil, tempPasswordExpiresAt: $tempPasswordExpiresAt, memberships: $memberships)';
}


}

/// @nodoc
abstract mixin class _$UserDetailCopyWith<$Res> implements $UserDetailCopyWith<$Res> {
  factory _$UserDetailCopyWith(_UserDetail value, $Res Function(_UserDetail) _then) = __$UserDetailCopyWithImpl;
@override @useResult
$Res call({
 String id, String externalId, String email, String displayName, bool isAppAdmin, bool isActive, bool hasPassword, bool mustChangePassword, DateTime? passwordChangedAt, DateTime? lockedUntil, DateTime? tempPasswordExpiresAt, List<UserMembership> memberships
});




}
/// @nodoc
class __$UserDetailCopyWithImpl<$Res>
    implements _$UserDetailCopyWith<$Res> {
  __$UserDetailCopyWithImpl(this._self, this._then);

  final _UserDetail _self;
  final $Res Function(_UserDetail) _then;

/// Create a copy of UserDetail
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? externalId = null,Object? email = null,Object? displayName = null,Object? isAppAdmin = null,Object? isActive = null,Object? hasPassword = null,Object? mustChangePassword = null,Object? passwordChangedAt = freezed,Object? lockedUntil = freezed,Object? tempPasswordExpiresAt = freezed,Object? memberships = null,}) {
  return _then(_UserDetail(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,externalId: null == externalId ? _self.externalId : externalId // ignore: cast_nullable_to_non_nullable
as String,email: null == email ? _self.email : email // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,isAppAdmin: null == isAppAdmin ? _self.isAppAdmin : isAppAdmin // ignore: cast_nullable_to_non_nullable
as bool,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,hasPassword: null == hasPassword ? _self.hasPassword : hasPassword // ignore: cast_nullable_to_non_nullable
as bool,mustChangePassword: null == mustChangePassword ? _self.mustChangePassword : mustChangePassword // ignore: cast_nullable_to_non_nullable
as bool,passwordChangedAt: freezed == passwordChangedAt ? _self.passwordChangedAt : passwordChangedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,lockedUntil: freezed == lockedUntil ? _self.lockedUntil : lockedUntil // ignore: cast_nullable_to_non_nullable
as DateTime?,tempPasswordExpiresAt: freezed == tempPasswordExpiresAt ? _self.tempPasswordExpiresAt : tempPasswordExpiresAt // ignore: cast_nullable_to_non_nullable
as DateTime?,memberships: null == memberships ? _self._memberships : memberships // ignore: cast_nullable_to_non_nullable
as List<UserMembership>,
  ));
}


}


/// @nodoc
mixin _$MatrixRow {

 String get action; String get label; String? get note; List<String> get roles;
/// Create a copy of MatrixRow
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MatrixRowCopyWith<MatrixRow> get copyWith => _$MatrixRowCopyWithImpl<MatrixRow>(this as MatrixRow, _$identity);

  /// Serializes this MatrixRow to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as MatrixRow;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MatrixRow&&(identical(other.action, _this.action) || other.action == _this.action)&&(identical(other.label, _this.label) || other.label == _this.label)&&(identical(other.note, _this.note) || other.note == _this.note)&&const DeepCollectionEquality().equals(other.roles, _this.roles));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as MatrixRow;
  return Object.hash(runtimeType,_this.action,_this.label,_this.note,const DeepCollectionEquality().hash(_this.roles));
}

@override
String toString() {
  final _this = this as MatrixRow;
  return 'MatrixRow(action: ${_this.action}, label: ${_this.label}, note: ${_this.note}, roles: ${_this.roles})';
}


}

/// @nodoc
abstract mixin class $MatrixRowCopyWith<$Res>  {
  factory $MatrixRowCopyWith(MatrixRow value, $Res Function(MatrixRow) _then) = _$MatrixRowCopyWithImpl;
@useResult
$Res call({
 String action, String label, String? note, List<String> roles
});




}
/// @nodoc
class _$MatrixRowCopyWithImpl<$Res>
    implements $MatrixRowCopyWith<$Res> {
  _$MatrixRowCopyWithImpl(this._self, this._then);

  final MatrixRow _self;
  final $Res Function(MatrixRow) _then;

/// Create a copy of MatrixRow
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? action = null,Object? label = null,Object? note = freezed,Object? roles = null,}) {
  return _then(MatrixRow(
action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,label: null == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,roles: null == roles ? _self.roles : roles // ignore: cast_nullable_to_non_nullable
as List<String>,
  ));
}

}


/// Adds pattern-matching-related methods to [MatrixRow].
extension MatrixRowPatterns on MatrixRow {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _MatrixRow value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _MatrixRow() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _MatrixRow value)  $default,){
final _that = this;
switch (_that) {
case _MatrixRow():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _MatrixRow value)?  $default,){
final _that = this;
switch (_that) {
case _MatrixRow() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String action,  String label,  String? note,  List<String> roles)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MatrixRow() when $default != null:
return $default(_that.action,_that.label,_that.note,_that.roles);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String action,  String label,  String? note,  List<String> roles)  $default,) {final _that = this;
switch (_that) {
case _MatrixRow():
return $default(_that.action,_that.label,_that.note,_that.roles);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String action,  String label,  String? note,  List<String> roles)?  $default,) {final _that = this;
switch (_that) {
case _MatrixRow() when $default != null:
return $default(_that.action,_that.label,_that.note,_that.roles);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MatrixRow implements MatrixRow {
  const _MatrixRow({required this.action, required this.label, this.note,  List<String> roles = const <String>[]}): _roles = roles;
  factory _MatrixRow.fromJson(Map<String, dynamic> json) => _$MatrixRowFromJson(json);

@override final  String action;
@override final  String label;
@override final  String? note;
 final  List<String> _roles;
@override@JsonKey() List<String> get roles {
  if (_roles is EqualUnmodifiableListView) return _roles;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_roles);
}


/// Create a copy of MatrixRow
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MatrixRowCopyWith<_MatrixRow> get copyWith => __$MatrixRowCopyWithImpl<_MatrixRow>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$MatrixRowToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _MatrixRow&&(identical(other.action, action) || other.action == action)&&(identical(other.label, label) || other.label == label)&&(identical(other.note, note) || other.note == note)&&const DeepCollectionEquality().equals(other.roles, _roles));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,action,label,note,const DeepCollectionEquality().hash(_roles));
}

@override
String toString() {
    return 'MatrixRow(action: $action, label: $label, note: $note, roles: $roles)';
}


}

/// @nodoc
abstract mixin class _$MatrixRowCopyWith<$Res> implements $MatrixRowCopyWith<$Res> {
  factory _$MatrixRowCopyWith(_MatrixRow value, $Res Function(_MatrixRow) _then) = __$MatrixRowCopyWithImpl;
@override @useResult
$Res call({
 String action, String label, String? note, List<String> roles
});




}
/// @nodoc
class __$MatrixRowCopyWithImpl<$Res>
    implements _$MatrixRowCopyWith<$Res> {
  __$MatrixRowCopyWithImpl(this._self, this._then);

  final _MatrixRow _self;
  final $Res Function(_MatrixRow) _then;

/// Create a copy of MatrixRow
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? action = null,Object? label = null,Object? note = freezed,Object? roles = null,}) {
  return _then(_MatrixRow(
action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,label: null == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,roles: null == roles ? _self._roles : roles // ignore: cast_nullable_to_non_nullable
as List<String>,
  ));
}


}


/// @nodoc
mixin _$ChangeActionRule {

 String get action; String get requires;
/// Create a copy of ChangeActionRule
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ChangeActionRuleCopyWith<ChangeActionRule> get copyWith => _$ChangeActionRuleCopyWithImpl<ChangeActionRule>(this as ChangeActionRule, _$identity);

  /// Serializes this ChangeActionRule to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ChangeActionRule;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ChangeActionRule&&(identical(other.action, _this.action) || other.action == _this.action)&&(identical(other.requires, _this.requires) || other.requires == _this.requires));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ChangeActionRule;
  return Object.hash(runtimeType,_this.action,_this.requires);
}

@override
String toString() {
  final _this = this as ChangeActionRule;
  return 'ChangeActionRule(action: ${_this.action}, requires: ${_this.requires})';
}


}

/// @nodoc
abstract mixin class $ChangeActionRuleCopyWith<$Res>  {
  factory $ChangeActionRuleCopyWith(ChangeActionRule value, $Res Function(ChangeActionRule) _then) = _$ChangeActionRuleCopyWithImpl;
@useResult
$Res call({
 String action, String requires
});




}
/// @nodoc
class _$ChangeActionRuleCopyWithImpl<$Res>
    implements $ChangeActionRuleCopyWith<$Res> {
  _$ChangeActionRuleCopyWithImpl(this._self, this._then);

  final ChangeActionRule _self;
  final $Res Function(ChangeActionRule) _then;

/// Create a copy of ChangeActionRule
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? action = null,Object? requires = null,}) {
  return _then(ChangeActionRule(
action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,requires: null == requires ? _self.requires : requires // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

}


/// Adds pattern-matching-related methods to [ChangeActionRule].
extension ChangeActionRulePatterns on ChangeActionRule {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ChangeActionRule value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ChangeActionRule() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ChangeActionRule value)  $default,){
final _that = this;
switch (_that) {
case _ChangeActionRule():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ChangeActionRule value)?  $default,){
final _that = this;
switch (_that) {
case _ChangeActionRule() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String action,  String requires)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ChangeActionRule() when $default != null:
return $default(_that.action,_that.requires);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String action,  String requires)  $default,) {final _that = this;
switch (_that) {
case _ChangeActionRule():
return $default(_that.action,_that.requires);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String action,  String requires)?  $default,) {final _that = this;
switch (_that) {
case _ChangeActionRule() when $default != null:
return $default(_that.action,_that.requires);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ChangeActionRule implements ChangeActionRule {
  const _ChangeActionRule({required this.action, required this.requires});
  factory _ChangeActionRule.fromJson(Map<String, dynamic> json) => _$ChangeActionRuleFromJson(json);

@override final  String action;
@override final  String requires;

/// Create a copy of ChangeActionRule
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ChangeActionRuleCopyWith<_ChangeActionRule> get copyWith => __$ChangeActionRuleCopyWithImpl<_ChangeActionRule>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ChangeActionRuleToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ChangeActionRule&&(identical(other.action, action) || other.action == action)&&(identical(other.requires, requires) || other.requires == requires));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,action,requires);
}

@override
String toString() {
    return 'ChangeActionRule(action: $action, requires: $requires)';
}


}

/// @nodoc
abstract mixin class _$ChangeActionRuleCopyWith<$Res> implements $ChangeActionRuleCopyWith<$Res> {
  factory _$ChangeActionRuleCopyWith(_ChangeActionRule value, $Res Function(_ChangeActionRule) _then) = __$ChangeActionRuleCopyWithImpl;
@override @useResult
$Res call({
 String action, String requires
});




}
/// @nodoc
class __$ChangeActionRuleCopyWithImpl<$Res>
    implements _$ChangeActionRuleCopyWith<$Res> {
  __$ChangeActionRuleCopyWithImpl(this._self, this._then);

  final _ChangeActionRule _self;
  final $Res Function(_ChangeActionRule) _then;

/// Create a copy of ChangeActionRule
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? action = null,Object? requires = null,}) {
  return _then(_ChangeActionRule(
action: null == action ? _self.action : action // ignore: cast_nullable_to_non_nullable
as String,requires: null == requires ? _self.requires : requires // ignore: cast_nullable_to_non_nullable
as String,
  ));
}


}


/// @nodoc
mixin _$PermissionMatrix {

 List<String> get roles; List<MatrixRow> get actions; List<ChangeActionRule> get changeActions;
/// Create a copy of PermissionMatrix
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$PermissionMatrixCopyWith<PermissionMatrix> get copyWith => _$PermissionMatrixCopyWithImpl<PermissionMatrix>(this as PermissionMatrix, _$identity);

  /// Serializes this PermissionMatrix to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as PermissionMatrix;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is PermissionMatrix&&const DeepCollectionEquality().equals(other.roles, _this.roles)&&const DeepCollectionEquality().equals(other.actions, _this.actions)&&const DeepCollectionEquality().equals(other.changeActions, _this.changeActions));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as PermissionMatrix;
  return Object.hash(runtimeType,const DeepCollectionEquality().hash(_this.roles),const DeepCollectionEquality().hash(_this.actions),const DeepCollectionEquality().hash(_this.changeActions));
}

@override
String toString() {
  final _this = this as PermissionMatrix;
  return 'PermissionMatrix(roles: ${_this.roles}, actions: ${_this.actions}, changeActions: ${_this.changeActions})';
}


}

/// @nodoc
abstract mixin class $PermissionMatrixCopyWith<$Res>  {
  factory $PermissionMatrixCopyWith(PermissionMatrix value, $Res Function(PermissionMatrix) _then) = _$PermissionMatrixCopyWithImpl;
@useResult
$Res call({
 List<String> roles, List<MatrixRow> actions, List<ChangeActionRule> changeActions
});




}
/// @nodoc
class _$PermissionMatrixCopyWithImpl<$Res>
    implements $PermissionMatrixCopyWith<$Res> {
  _$PermissionMatrixCopyWithImpl(this._self, this._then);

  final PermissionMatrix _self;
  final $Res Function(PermissionMatrix) _then;

/// Create a copy of PermissionMatrix
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? roles = null,Object? actions = null,Object? changeActions = null,}) {
  return _then(PermissionMatrix(
roles: null == roles ? _self.roles : roles // ignore: cast_nullable_to_non_nullable
as List<String>,actions: null == actions ? _self.actions : actions // ignore: cast_nullable_to_non_nullable
as List<MatrixRow>,changeActions: null == changeActions ? _self.changeActions : changeActions // ignore: cast_nullable_to_non_nullable
as List<ChangeActionRule>,
  ));
}

}


/// Adds pattern-matching-related methods to [PermissionMatrix].
extension PermissionMatrixPatterns on PermissionMatrix {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _PermissionMatrix value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _PermissionMatrix() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _PermissionMatrix value)  $default,){
final _that = this;
switch (_that) {
case _PermissionMatrix():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _PermissionMatrix value)?  $default,){
final _that = this;
switch (_that) {
case _PermissionMatrix() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( List<String> roles,  List<MatrixRow> actions,  List<ChangeActionRule> changeActions)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _PermissionMatrix() when $default != null:
return $default(_that.roles,_that.actions,_that.changeActions);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( List<String> roles,  List<MatrixRow> actions,  List<ChangeActionRule> changeActions)  $default,) {final _that = this;
switch (_that) {
case _PermissionMatrix():
return $default(_that.roles,_that.actions,_that.changeActions);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( List<String> roles,  List<MatrixRow> actions,  List<ChangeActionRule> changeActions)?  $default,) {final _that = this;
switch (_that) {
case _PermissionMatrix() when $default != null:
return $default(_that.roles,_that.actions,_that.changeActions);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _PermissionMatrix implements PermissionMatrix {
  const _PermissionMatrix({required  List<String> roles, required  List<MatrixRow> actions,  List<ChangeActionRule> changeActions = const <ChangeActionRule>[]}): _roles = roles,_actions = actions,_changeActions = changeActions;
  factory _PermissionMatrix.fromJson(Map<String, dynamic> json) => _$PermissionMatrixFromJson(json);

 final  List<String> _roles;
@override List<String> get roles {
  if (_roles is EqualUnmodifiableListView) return _roles;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_roles);
}

 final  List<MatrixRow> _actions;
@override List<MatrixRow> get actions {
  if (_actions is EqualUnmodifiableListView) return _actions;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_actions);
}

 final  List<ChangeActionRule> _changeActions;
@override@JsonKey() List<ChangeActionRule> get changeActions {
  if (_changeActions is EqualUnmodifiableListView) return _changeActions;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_changeActions);
}


/// Create a copy of PermissionMatrix
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$PermissionMatrixCopyWith<_PermissionMatrix> get copyWith => __$PermissionMatrixCopyWithImpl<_PermissionMatrix>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$PermissionMatrixToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _PermissionMatrix&&const DeepCollectionEquality().equals(other.roles, _roles)&&const DeepCollectionEquality().equals(other.actions, _actions)&&const DeepCollectionEquality().equals(other.changeActions, _changeActions));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,const DeepCollectionEquality().hash(_roles),const DeepCollectionEquality().hash(_actions),const DeepCollectionEquality().hash(_changeActions));
}

@override
String toString() {
    return 'PermissionMatrix(roles: $roles, actions: $actions, changeActions: $changeActions)';
}


}

/// @nodoc
abstract mixin class _$PermissionMatrixCopyWith<$Res> implements $PermissionMatrixCopyWith<$Res> {
  factory _$PermissionMatrixCopyWith(_PermissionMatrix value, $Res Function(_PermissionMatrix) _then) = __$PermissionMatrixCopyWithImpl;
@override @useResult
$Res call({
 List<String> roles, List<MatrixRow> actions, List<ChangeActionRule> changeActions
});




}
/// @nodoc
class __$PermissionMatrixCopyWithImpl<$Res>
    implements _$PermissionMatrixCopyWith<$Res> {
  __$PermissionMatrixCopyWithImpl(this._self, this._then);

  final _PermissionMatrix _self;
  final $Res Function(_PermissionMatrix) _then;

/// Create a copy of PermissionMatrix
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? roles = null,Object? actions = null,Object? changeActions = null,}) {
  return _then(_PermissionMatrix(
roles: null == roles ? _self._roles : roles // ignore: cast_nullable_to_non_nullable
as List<String>,actions: null == actions ? _self._actions : actions // ignore: cast_nullable_to_non_nullable
as List<MatrixRow>,changeActions: null == changeActions ? _self._changeActions : changeActions // ignore: cast_nullable_to_non_nullable
as List<ChangeActionRule>,
  ));
}


}

// dart format on
