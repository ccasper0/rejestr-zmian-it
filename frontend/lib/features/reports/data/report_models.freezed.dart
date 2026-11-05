// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint, type=warning, deprecated_member_use, deprecated_member_use_from_same_package
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'report_models.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$ReportCompany {

 String get id; String get name; String get prefix;
/// Create a copy of ReportCompany
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ReportCompanyCopyWith<ReportCompany> get copyWith => _$ReportCompanyCopyWithImpl<ReportCompany>(this as ReportCompany, _$identity);

  /// Serializes this ReportCompany to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ReportCompany;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ReportCompany&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.name, _this.name) || other.name == _this.name)&&(identical(other.prefix, _this.prefix) || other.prefix == _this.prefix));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ReportCompany;
  return Object.hash(runtimeType,_this.id,_this.name,_this.prefix);
}

@override
String toString() {
  final _this = this as ReportCompany;
  return 'ReportCompany(id: ${_this.id}, name: ${_this.name}, prefix: ${_this.prefix})';
}


}

/// @nodoc
abstract mixin class $ReportCompanyCopyWith<$Res>  {
  factory $ReportCompanyCopyWith(ReportCompany value, $Res Function(ReportCompany) _then) = _$ReportCompanyCopyWithImpl;
@useResult
$Res call({
 String id, String name, String prefix
});




}
/// @nodoc
class _$ReportCompanyCopyWithImpl<$Res>
    implements $ReportCompanyCopyWith<$Res> {
  _$ReportCompanyCopyWithImpl(this._self, this._then);

  final ReportCompany _self;
  final $Res Function(ReportCompany) _then;

/// Create a copy of ReportCompany
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? name = null,Object? prefix = null,}) {
  return _then(ReportCompany(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,prefix: null == prefix ? _self.prefix : prefix // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

}


/// Adds pattern-matching-related methods to [ReportCompany].
extension ReportCompanyPatterns on ReportCompany {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ReportCompany value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ReportCompany() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ReportCompany value)  $default,){
final _that = this;
switch (_that) {
case _ReportCompany():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ReportCompany value)?  $default,){
final _that = this;
switch (_that) {
case _ReportCompany() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String name,  String prefix)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ReportCompany() when $default != null:
return $default(_that.id,_that.name,_that.prefix);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String name,  String prefix)  $default,) {final _that = this;
switch (_that) {
case _ReportCompany():
return $default(_that.id,_that.name,_that.prefix);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String name,  String prefix)?  $default,) {final _that = this;
switch (_that) {
case _ReportCompany() when $default != null:
return $default(_that.id,_that.name,_that.prefix);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ReportCompany implements ReportCompany {
  const _ReportCompany({required this.id, required this.name, required this.prefix});
  factory _ReportCompany.fromJson(Map<String, dynamic> json) => _$ReportCompanyFromJson(json);

@override final  String id;
@override final  String name;
@override final  String prefix;

/// Create a copy of ReportCompany
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ReportCompanyCopyWith<_ReportCompany> get copyWith => __$ReportCompanyCopyWithImpl<_ReportCompany>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ReportCompanyToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ReportCompany&&(identical(other.id, id) || other.id == id)&&(identical(other.name, name) || other.name == name)&&(identical(other.prefix, prefix) || other.prefix == prefix));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,id,name,prefix);
}

@override
String toString() {
    return 'ReportCompany(id: $id, name: $name, prefix: $prefix)';
}


}

/// @nodoc
abstract mixin class _$ReportCompanyCopyWith<$Res> implements $ReportCompanyCopyWith<$Res> {
  factory _$ReportCompanyCopyWith(_ReportCompany value, $Res Function(_ReportCompany) _then) = __$ReportCompanyCopyWithImpl;
@override @useResult
$Res call({
 String id, String name, String prefix
});




}
/// @nodoc
class __$ReportCompanyCopyWithImpl<$Res>
    implements _$ReportCompanyCopyWith<$Res> {
  __$ReportCompanyCopyWithImpl(this._self, this._then);

  final _ReportCompany _self;
  final $Res Function(_ReportCompany) _then;

/// Create a copy of ReportCompany
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? name = null,Object? prefix = null,}) {
  return _then(_ReportCompany(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,prefix: null == prefix ? _self.prefix : prefix // ignore: cast_nullable_to_non_nullable
as String,
  ));
}


}


/// @nodoc
mixin _$Report {

 String get id; String get number; String get kind; String get format; String get status;/// null = the multi-company report of an auditor.
 String? get companyId; ReportCompany? get company; List<ReportCompany> get companies; String? get changeId; String? get changeNumber; DateTime? get periodFrom; DateTime? get periodTo; Map<String, dynamic> get filters; bool get includeAuditTrail; UserRef get generatedBy; DateTime get createdAt; DateTime? get completedAt; int? get changeCount; String? get dataSha256; String? get fileSha256; int? get size; String? get error; String? get downloadUrl;
/// Create a copy of Report
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ReportCopyWith<Report> get copyWith => _$ReportCopyWithImpl<Report>(this as Report, _$identity);

  /// Serializes this Report to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as Report;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Report&&(identical(other.id, _this.id) || other.id == _this.id)&&(identical(other.number, _this.number) || other.number == _this.number)&&(identical(other.kind, _this.kind) || other.kind == _this.kind)&&(identical(other.format, _this.format) || other.format == _this.format)&&(identical(other.status, _this.status) || other.status == _this.status)&&(identical(other.companyId, _this.companyId) || other.companyId == _this.companyId)&&(identical(other.company, _this.company) || other.company == _this.company)&&const DeepCollectionEquality().equals(other.companies, _this.companies)&&(identical(other.changeId, _this.changeId) || other.changeId == _this.changeId)&&(identical(other.changeNumber, _this.changeNumber) || other.changeNumber == _this.changeNumber)&&(identical(other.periodFrom, _this.periodFrom) || other.periodFrom == _this.periodFrom)&&(identical(other.periodTo, _this.periodTo) || other.periodTo == _this.periodTo)&&const DeepCollectionEquality().equals(other.filters, _this.filters)&&(identical(other.includeAuditTrail, _this.includeAuditTrail) || other.includeAuditTrail == _this.includeAuditTrail)&&(identical(other.generatedBy, _this.generatedBy) || other.generatedBy == _this.generatedBy)&&(identical(other.createdAt, _this.createdAt) || other.createdAt == _this.createdAt)&&(identical(other.completedAt, _this.completedAt) || other.completedAt == _this.completedAt)&&(identical(other.changeCount, _this.changeCount) || other.changeCount == _this.changeCount)&&(identical(other.dataSha256, _this.dataSha256) || other.dataSha256 == _this.dataSha256)&&(identical(other.fileSha256, _this.fileSha256) || other.fileSha256 == _this.fileSha256)&&(identical(other.size, _this.size) || other.size == _this.size)&&(identical(other.error, _this.error) || other.error == _this.error)&&(identical(other.downloadUrl, _this.downloadUrl) || other.downloadUrl == _this.downloadUrl));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as Report;
  return Object.hashAll([runtimeType,_this.id,_this.number,_this.kind,_this.format,_this.status,_this.companyId,_this.company,const DeepCollectionEquality().hash(_this.companies),_this.changeId,_this.changeNumber,_this.periodFrom,_this.periodTo,const DeepCollectionEquality().hash(_this.filters),_this.includeAuditTrail,_this.generatedBy,_this.createdAt,_this.completedAt,_this.changeCount,_this.dataSha256,_this.fileSha256,_this.size,_this.error,_this.downloadUrl]);
}

@override
String toString() {
  final _this = this as Report;
  return 'Report(id: ${_this.id}, number: ${_this.number}, kind: ${_this.kind}, format: ${_this.format}, status: ${_this.status}, companyId: ${_this.companyId}, company: ${_this.company}, companies: ${_this.companies}, changeId: ${_this.changeId}, changeNumber: ${_this.changeNumber}, periodFrom: ${_this.periodFrom}, periodTo: ${_this.periodTo}, filters: ${_this.filters}, includeAuditTrail: ${_this.includeAuditTrail}, generatedBy: ${_this.generatedBy}, createdAt: ${_this.createdAt}, completedAt: ${_this.completedAt}, changeCount: ${_this.changeCount}, dataSha256: ${_this.dataSha256}, fileSha256: ${_this.fileSha256}, size: ${_this.size}, error: ${_this.error}, downloadUrl: ${_this.downloadUrl})';
}


}

/// @nodoc
abstract mixin class $ReportCopyWith<$Res>  {
  factory $ReportCopyWith(Report value, $Res Function(Report) _then) = _$ReportCopyWithImpl;
@useResult
$Res call({
 String id, String number, String kind, String format, String status, String? companyId, ReportCompany? company, List<ReportCompany> companies, String? changeId, String? changeNumber, DateTime? periodFrom, DateTime? periodTo, Map<String, dynamic> filters, bool includeAuditTrail, UserRef generatedBy, DateTime createdAt, DateTime? completedAt, int? changeCount, String? dataSha256, String? fileSha256, int? size, String? error, String? downloadUrl
});


$ReportCompanyCopyWith<$Res>? get company;$UserRefCopyWith<$Res> get generatedBy;

}
/// @nodoc
class _$ReportCopyWithImpl<$Res>
    implements $ReportCopyWith<$Res> {
  _$ReportCopyWithImpl(this._self, this._then);

  final Report _self;
  final $Res Function(Report) _then;

/// Create a copy of Report
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? number = null,Object? kind = null,Object? format = null,Object? status = null,Object? companyId = freezed,Object? company = freezed,Object? companies = null,Object? changeId = freezed,Object? changeNumber = freezed,Object? periodFrom = freezed,Object? periodTo = freezed,Object? filters = null,Object? includeAuditTrail = null,Object? generatedBy = null,Object? createdAt = null,Object? completedAt = freezed,Object? changeCount = freezed,Object? dataSha256 = freezed,Object? fileSha256 = freezed,Object? size = freezed,Object? error = freezed,Object? downloadUrl = freezed,}) {
  return _then(Report(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,number: null == number ? _self.number : number // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as String,format: null == format ? _self.format : format // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,company: freezed == company ? _self.company : company // ignore: cast_nullable_to_non_nullable
as ReportCompany?,companies: null == companies ? _self.companies : companies // ignore: cast_nullable_to_non_nullable
as List<ReportCompany>,changeId: freezed == changeId ? _self.changeId : changeId // ignore: cast_nullable_to_non_nullable
as String?,changeNumber: freezed == changeNumber ? _self.changeNumber : changeNumber // ignore: cast_nullable_to_non_nullable
as String?,periodFrom: freezed == periodFrom ? _self.periodFrom : periodFrom // ignore: cast_nullable_to_non_nullable
as DateTime?,periodTo: freezed == periodTo ? _self.periodTo : periodTo // ignore: cast_nullable_to_non_nullable
as DateTime?,filters: null == filters ? _self.filters : filters // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,includeAuditTrail: null == includeAuditTrail ? _self.includeAuditTrail : includeAuditTrail // ignore: cast_nullable_to_non_nullable
as bool,generatedBy: null == generatedBy ? _self.generatedBy : generatedBy // ignore: cast_nullable_to_non_nullable
as UserRef,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,completedAt: freezed == completedAt ? _self.completedAt : completedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,changeCount: freezed == changeCount ? _self.changeCount : changeCount // ignore: cast_nullable_to_non_nullable
as int?,dataSha256: freezed == dataSha256 ? _self.dataSha256 : dataSha256 // ignore: cast_nullable_to_non_nullable
as String?,fileSha256: freezed == fileSha256 ? _self.fileSha256 : fileSha256 // ignore: cast_nullable_to_non_nullable
as String?,size: freezed == size ? _self.size : size // ignore: cast_nullable_to_non_nullable
as int?,error: freezed == error ? _self.error : error // ignore: cast_nullable_to_non_nullable
as String?,downloadUrl: freezed == downloadUrl ? _self.downloadUrl : downloadUrl // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of Report
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$ReportCompanyCopyWith<$Res>? get company {
    if (_self.company == null) {
    return null;
  }

  return $ReportCompanyCopyWith<$Res>(_self.company!, (value) {
    return _then(_self.copyWith(company: value));
  });
}/// Create a copy of Report
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get generatedBy {
  
  return $UserRefCopyWith<$Res>(_self.generatedBy, (value) {
    return _then(_self.copyWith(generatedBy: value));
  });
}
}


/// Adds pattern-matching-related methods to [Report].
extension ReportPatterns on Report {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Report value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Report() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Report value)  $default,){
final _that = this;
switch (_that) {
case _Report():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Report value)?  $default,){
final _that = this;
switch (_that) {
case _Report() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String number,  String kind,  String format,  String status,  String? companyId,  ReportCompany? company,  List<ReportCompany> companies,  String? changeId,  String? changeNumber,  DateTime? periodFrom,  DateTime? periodTo,  Map<String, dynamic> filters,  bool includeAuditTrail,  UserRef generatedBy,  DateTime createdAt,  DateTime? completedAt,  int? changeCount,  String? dataSha256,  String? fileSha256,  int? size,  String? error,  String? downloadUrl)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Report() when $default != null:
return $default(_that.id,_that.number,_that.kind,_that.format,_that.status,_that.companyId,_that.company,_that.companies,_that.changeId,_that.changeNumber,_that.periodFrom,_that.periodTo,_that.filters,_that.includeAuditTrail,_that.generatedBy,_that.createdAt,_that.completedAt,_that.changeCount,_that.dataSha256,_that.fileSha256,_that.size,_that.error,_that.downloadUrl);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String number,  String kind,  String format,  String status,  String? companyId,  ReportCompany? company,  List<ReportCompany> companies,  String? changeId,  String? changeNumber,  DateTime? periodFrom,  DateTime? periodTo,  Map<String, dynamic> filters,  bool includeAuditTrail,  UserRef generatedBy,  DateTime createdAt,  DateTime? completedAt,  int? changeCount,  String? dataSha256,  String? fileSha256,  int? size,  String? error,  String? downloadUrl)  $default,) {final _that = this;
switch (_that) {
case _Report():
return $default(_that.id,_that.number,_that.kind,_that.format,_that.status,_that.companyId,_that.company,_that.companies,_that.changeId,_that.changeNumber,_that.periodFrom,_that.periodTo,_that.filters,_that.includeAuditTrail,_that.generatedBy,_that.createdAt,_that.completedAt,_that.changeCount,_that.dataSha256,_that.fileSha256,_that.size,_that.error,_that.downloadUrl);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String number,  String kind,  String format,  String status,  String? companyId,  ReportCompany? company,  List<ReportCompany> companies,  String? changeId,  String? changeNumber,  DateTime? periodFrom,  DateTime? periodTo,  Map<String, dynamic> filters,  bool includeAuditTrail,  UserRef generatedBy,  DateTime createdAt,  DateTime? completedAt,  int? changeCount,  String? dataSha256,  String? fileSha256,  int? size,  String? error,  String? downloadUrl)?  $default,) {final _that = this;
switch (_that) {
case _Report() when $default != null:
return $default(_that.id,_that.number,_that.kind,_that.format,_that.status,_that.companyId,_that.company,_that.companies,_that.changeId,_that.changeNumber,_that.periodFrom,_that.periodTo,_that.filters,_that.includeAuditTrail,_that.generatedBy,_that.createdAt,_that.completedAt,_that.changeCount,_that.dataSha256,_that.fileSha256,_that.size,_that.error,_that.downloadUrl);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Report extends Report {
  const _Report({required this.id, required this.number, required this.kind, required this.format, required this.status, this.companyId, this.company,  List<ReportCompany> companies = const <ReportCompany>[], this.changeId, this.changeNumber, this.periodFrom, this.periodTo,  Map<String, dynamic> filters = const <String, dynamic>{}, this.includeAuditTrail = false, required this.generatedBy, required this.createdAt, this.completedAt, this.changeCount, this.dataSha256, this.fileSha256, this.size, this.error, this.downloadUrl}): _companies = companies,_filters = filters,super._();
  factory _Report.fromJson(Map<String, dynamic> json) => _$ReportFromJson(json);

@override final  String id;
@override final  String number;
@override final  String kind;
@override final  String format;
@override final  String status;
/// null = the multi-company report of an auditor.
@override final  String? companyId;
@override final  ReportCompany? company;
 final  List<ReportCompany> _companies;
@override@JsonKey() List<ReportCompany> get companies {
  if (_companies is EqualUnmodifiableListView) return _companies;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_companies);
}

@override final  String? changeId;
@override final  String? changeNumber;
@override final  DateTime? periodFrom;
@override final  DateTime? periodTo;
 final  Map<String, dynamic> _filters;
@override@JsonKey() Map<String, dynamic> get filters {
  if (_filters is EqualUnmodifiableMapView) return _filters;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_filters);
}

@override@JsonKey() final  bool includeAuditTrail;
@override final  UserRef generatedBy;
@override final  DateTime createdAt;
@override final  DateTime? completedAt;
@override final  int? changeCount;
@override final  String? dataSha256;
@override final  String? fileSha256;
@override final  int? size;
@override final  String? error;
@override final  String? downloadUrl;

/// Create a copy of Report
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ReportCopyWith<_Report> get copyWith => __$ReportCopyWithImpl<_Report>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ReportToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _Report&&(identical(other.id, id) || other.id == id)&&(identical(other.number, number) || other.number == number)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.format, format) || other.format == format)&&(identical(other.status, status) || other.status == status)&&(identical(other.companyId, companyId) || other.companyId == companyId)&&(identical(other.company, company) || other.company == company)&&const DeepCollectionEquality().equals(other.companies, _companies)&&(identical(other.changeId, changeId) || other.changeId == changeId)&&(identical(other.changeNumber, changeNumber) || other.changeNumber == changeNumber)&&(identical(other.periodFrom, periodFrom) || other.periodFrom == periodFrom)&&(identical(other.periodTo, periodTo) || other.periodTo == periodTo)&&const DeepCollectionEquality().equals(other.filters, _filters)&&(identical(other.includeAuditTrail, includeAuditTrail) || other.includeAuditTrail == includeAuditTrail)&&(identical(other.generatedBy, generatedBy) || other.generatedBy == generatedBy)&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt)&&(identical(other.completedAt, completedAt) || other.completedAt == completedAt)&&(identical(other.changeCount, changeCount) || other.changeCount == changeCount)&&(identical(other.dataSha256, dataSha256) || other.dataSha256 == dataSha256)&&(identical(other.fileSha256, fileSha256) || other.fileSha256 == fileSha256)&&(identical(other.size, size) || other.size == size)&&(identical(other.error, error) || other.error == error)&&(identical(other.downloadUrl, downloadUrl) || other.downloadUrl == downloadUrl));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hashAll([runtimeType,id,number,kind,format,status,companyId,company,const DeepCollectionEquality().hash(_companies),changeId,changeNumber,periodFrom,periodTo,const DeepCollectionEquality().hash(_filters),includeAuditTrail,generatedBy,createdAt,completedAt,changeCount,dataSha256,fileSha256,size,error,downloadUrl]);
}

@override
String toString() {
    return 'Report(id: $id, number: $number, kind: $kind, format: $format, status: $status, companyId: $companyId, company: $company, companies: $companies, changeId: $changeId, changeNumber: $changeNumber, periodFrom: $periodFrom, periodTo: $periodTo, filters: $filters, includeAuditTrail: $includeAuditTrail, generatedBy: $generatedBy, createdAt: $createdAt, completedAt: $completedAt, changeCount: $changeCount, dataSha256: $dataSha256, fileSha256: $fileSha256, size: $size, error: $error, downloadUrl: $downloadUrl)';
}


}

/// @nodoc
abstract mixin class _$ReportCopyWith<$Res> implements $ReportCopyWith<$Res> {
  factory _$ReportCopyWith(_Report value, $Res Function(_Report) _then) = __$ReportCopyWithImpl;
@override @useResult
$Res call({
 String id, String number, String kind, String format, String status, String? companyId, ReportCompany? company, List<ReportCompany> companies, String? changeId, String? changeNumber, DateTime? periodFrom, DateTime? periodTo, Map<String, dynamic> filters, bool includeAuditTrail, UserRef generatedBy, DateTime createdAt, DateTime? completedAt, int? changeCount, String? dataSha256, String? fileSha256, int? size, String? error, String? downloadUrl
});


@override $ReportCompanyCopyWith<$Res>? get company;@override $UserRefCopyWith<$Res> get generatedBy;

}
/// @nodoc
class __$ReportCopyWithImpl<$Res>
    implements _$ReportCopyWith<$Res> {
  __$ReportCopyWithImpl(this._self, this._then);

  final _Report _self;
  final $Res Function(_Report) _then;

/// Create a copy of Report
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? number = null,Object? kind = null,Object? format = null,Object? status = null,Object? companyId = freezed,Object? company = freezed,Object? companies = null,Object? changeId = freezed,Object? changeNumber = freezed,Object? periodFrom = freezed,Object? periodTo = freezed,Object? filters = null,Object? includeAuditTrail = null,Object? generatedBy = null,Object? createdAt = null,Object? completedAt = freezed,Object? changeCount = freezed,Object? dataSha256 = freezed,Object? fileSha256 = freezed,Object? size = freezed,Object? error = freezed,Object? downloadUrl = freezed,}) {
  return _then(_Report(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,number: null == number ? _self.number : number // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as String,format: null == format ? _self.format : format // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,company: freezed == company ? _self.company : company // ignore: cast_nullable_to_non_nullable
as ReportCompany?,companies: null == companies ? _self._companies : companies // ignore: cast_nullable_to_non_nullable
as List<ReportCompany>,changeId: freezed == changeId ? _self.changeId : changeId // ignore: cast_nullable_to_non_nullable
as String?,changeNumber: freezed == changeNumber ? _self.changeNumber : changeNumber // ignore: cast_nullable_to_non_nullable
as String?,periodFrom: freezed == periodFrom ? _self.periodFrom : periodFrom // ignore: cast_nullable_to_non_nullable
as DateTime?,periodTo: freezed == periodTo ? _self.periodTo : periodTo // ignore: cast_nullable_to_non_nullable
as DateTime?,filters: null == filters ? _self._filters : filters // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,includeAuditTrail: null == includeAuditTrail ? _self.includeAuditTrail : includeAuditTrail // ignore: cast_nullable_to_non_nullable
as bool,generatedBy: null == generatedBy ? _self.generatedBy : generatedBy // ignore: cast_nullable_to_non_nullable
as UserRef,createdAt: null == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as DateTime,completedAt: freezed == completedAt ? _self.completedAt : completedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,changeCount: freezed == changeCount ? _self.changeCount : changeCount // ignore: cast_nullable_to_non_nullable
as int?,dataSha256: freezed == dataSha256 ? _self.dataSha256 : dataSha256 // ignore: cast_nullable_to_non_nullable
as String?,fileSha256: freezed == fileSha256 ? _self.fileSha256 : fileSha256 // ignore: cast_nullable_to_non_nullable
as String?,size: freezed == size ? _self.size : size // ignore: cast_nullable_to_non_nullable
as int?,error: freezed == error ? _self.error : error // ignore: cast_nullable_to_non_nullable
as String?,downloadUrl: freezed == downloadUrl ? _self.downloadUrl : downloadUrl // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of Report
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$ReportCompanyCopyWith<$Res>? get company {
    if (_self.company == null) {
    return null;
  }

  return $ReportCompanyCopyWith<$Res>(_self.company!, (value) {
    return _then(_self.copyWith(company: value));
  });
}/// Create a copy of Report
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$UserRefCopyWith<$Res> get generatedBy {
  
  return $UserRefCopyWith<$Res>(_self.generatedBy, (value) {
    return _then(_self.copyWith(generatedBy: value));
  });
}
}


/// @nodoc
mixin _$ReportFilterSet {

 String get periodBy; List<String> get status; List<String> get type; List<String> get category; List<String> get ci; String? get assignee; String? get approver;/// User id or `system`.
 String? get approvedBy; String? get q;
/// Create a copy of ReportFilterSet
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ReportFilterSetCopyWith<ReportFilterSet> get copyWith => _$ReportFilterSetCopyWithImpl<ReportFilterSet>(this as ReportFilterSet, _$identity);

  /// Serializes this ReportFilterSet to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ReportFilterSet;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ReportFilterSet&&(identical(other.periodBy, _this.periodBy) || other.periodBy == _this.periodBy)&&const DeepCollectionEquality().equals(other.status, _this.status)&&const DeepCollectionEquality().equals(other.type, _this.type)&&const DeepCollectionEquality().equals(other.category, _this.category)&&const DeepCollectionEquality().equals(other.ci, _this.ci)&&(identical(other.assignee, _this.assignee) || other.assignee == _this.assignee)&&(identical(other.approver, _this.approver) || other.approver == _this.approver)&&(identical(other.approvedBy, _this.approvedBy) || other.approvedBy == _this.approvedBy)&&(identical(other.q, _this.q) || other.q == _this.q));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ReportFilterSet;
  return Object.hash(runtimeType,_this.periodBy,const DeepCollectionEquality().hash(_this.status),const DeepCollectionEquality().hash(_this.type),const DeepCollectionEquality().hash(_this.category),const DeepCollectionEquality().hash(_this.ci),_this.assignee,_this.approver,_this.approvedBy,_this.q);
}

@override
String toString() {
  final _this = this as ReportFilterSet;
  return 'ReportFilterSet(periodBy: ${_this.periodBy}, status: ${_this.status}, type: ${_this.type}, category: ${_this.category}, ci: ${_this.ci}, assignee: ${_this.assignee}, approver: ${_this.approver}, approvedBy: ${_this.approvedBy}, q: ${_this.q})';
}


}

/// @nodoc
abstract mixin class $ReportFilterSetCopyWith<$Res>  {
  factory $ReportFilterSetCopyWith(ReportFilterSet value, $Res Function(ReportFilterSet) _then) = _$ReportFilterSetCopyWithImpl;
@useResult
$Res call({
 String periodBy, List<String> status, List<String> type, List<String> category, List<String> ci, String? assignee, String? approver, String? approvedBy, String? q
});




}
/// @nodoc
class _$ReportFilterSetCopyWithImpl<$Res>
    implements $ReportFilterSetCopyWith<$Res> {
  _$ReportFilterSetCopyWithImpl(this._self, this._then);

  final ReportFilterSet _self;
  final $Res Function(ReportFilterSet) _then;

/// Create a copy of ReportFilterSet
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? periodBy = null,Object? status = null,Object? type = null,Object? category = null,Object? ci = null,Object? assignee = freezed,Object? approver = freezed,Object? approvedBy = freezed,Object? q = freezed,}) {
  return _then(ReportFilterSet(
periodBy: null == periodBy ? _self.periodBy : periodBy // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as List<String>,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as List<String>,category: null == category ? _self.category : category // ignore: cast_nullable_to_non_nullable
as List<String>,ci: null == ci ? _self.ci : ci // ignore: cast_nullable_to_non_nullable
as List<String>,assignee: freezed == assignee ? _self.assignee : assignee // ignore: cast_nullable_to_non_nullable
as String?,approver: freezed == approver ? _self.approver : approver // ignore: cast_nullable_to_non_nullable
as String?,approvedBy: freezed == approvedBy ? _self.approvedBy : approvedBy // ignore: cast_nullable_to_non_nullable
as String?,q: freezed == q ? _self.q : q // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [ReportFilterSet].
extension ReportFilterSetPatterns on ReportFilterSet {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ReportFilterSet value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ReportFilterSet() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ReportFilterSet value)  $default,){
final _that = this;
switch (_that) {
case _ReportFilterSet():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ReportFilterSet value)?  $default,){
final _that = this;
switch (_that) {
case _ReportFilterSet() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String periodBy,  List<String> status,  List<String> type,  List<String> category,  List<String> ci,  String? assignee,  String? approver,  String? approvedBy,  String? q)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ReportFilterSet() when $default != null:
return $default(_that.periodBy,_that.status,_that.type,_that.category,_that.ci,_that.assignee,_that.approver,_that.approvedBy,_that.q);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String periodBy,  List<String> status,  List<String> type,  List<String> category,  List<String> ci,  String? assignee,  String? approver,  String? approvedBy,  String? q)  $default,) {final _that = this;
switch (_that) {
case _ReportFilterSet():
return $default(_that.periodBy,_that.status,_that.type,_that.category,_that.ci,_that.assignee,_that.approver,_that.approvedBy,_that.q);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String periodBy,  List<String> status,  List<String> type,  List<String> category,  List<String> ci,  String? assignee,  String? approver,  String? approvedBy,  String? q)?  $default,) {final _that = this;
switch (_that) {
case _ReportFilterSet() when $default != null:
return $default(_that.periodBy,_that.status,_that.type,_that.category,_that.ci,_that.assignee,_that.approver,_that.approvedBy,_that.q);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ReportFilterSet implements ReportFilterSet {
  const _ReportFilterSet({this.periodBy = 'created',  List<String> status = const <String>[],  List<String> type = const <String>[],  List<String> category = const <String>[],  List<String> ci = const <String>[], this.assignee, this.approver, this.approvedBy, this.q}): _status = status,_type = type,_category = category,_ci = ci;
  factory _ReportFilterSet.fromJson(Map<String, dynamic> json) => _$ReportFilterSetFromJson(json);

@override@JsonKey() final  String periodBy;
 final  List<String> _status;
@override@JsonKey() List<String> get status {
  if (_status is EqualUnmodifiableListView) return _status;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_status);
}

 final  List<String> _type;
@override@JsonKey() List<String> get type {
  if (_type is EqualUnmodifiableListView) return _type;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_type);
}

 final  List<String> _category;
@override@JsonKey() List<String> get category {
  if (_category is EqualUnmodifiableListView) return _category;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_category);
}

 final  List<String> _ci;
@override@JsonKey() List<String> get ci {
  if (_ci is EqualUnmodifiableListView) return _ci;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_ci);
}

@override final  String? assignee;
@override final  String? approver;
/// User id or `system`.
@override final  String? approvedBy;
@override final  String? q;

/// Create a copy of ReportFilterSet
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ReportFilterSetCopyWith<_ReportFilterSet> get copyWith => __$ReportFilterSetCopyWithImpl<_ReportFilterSet>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ReportFilterSetToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ReportFilterSet&&(identical(other.periodBy, periodBy) || other.periodBy == periodBy)&&const DeepCollectionEquality().equals(other.status, _status)&&const DeepCollectionEquality().equals(other.type, _type)&&const DeepCollectionEquality().equals(other.category, _category)&&const DeepCollectionEquality().equals(other.ci, _ci)&&(identical(other.assignee, assignee) || other.assignee == assignee)&&(identical(other.approver, approver) || other.approver == approver)&&(identical(other.approvedBy, approvedBy) || other.approvedBy == approvedBy)&&(identical(other.q, q) || other.q == q));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,periodBy,const DeepCollectionEquality().hash(_status),const DeepCollectionEquality().hash(_type),const DeepCollectionEquality().hash(_category),const DeepCollectionEquality().hash(_ci),assignee,approver,approvedBy,q);
}

@override
String toString() {
    return 'ReportFilterSet(periodBy: $periodBy, status: $status, type: $type, category: $category, ci: $ci, assignee: $assignee, approver: $approver, approvedBy: $approvedBy, q: $q)';
}


}

/// @nodoc
abstract mixin class _$ReportFilterSetCopyWith<$Res> implements $ReportFilterSetCopyWith<$Res> {
  factory _$ReportFilterSetCopyWith(_ReportFilterSet value, $Res Function(_ReportFilterSet) _then) = __$ReportFilterSetCopyWithImpl;
@override @useResult
$Res call({
 String periodBy, List<String> status, List<String> type, List<String> category, List<String> ci, String? assignee, String? approver, String? approvedBy, String? q
});




}
/// @nodoc
class __$ReportFilterSetCopyWithImpl<$Res>
    implements _$ReportFilterSetCopyWith<$Res> {
  __$ReportFilterSetCopyWithImpl(this._self, this._then);

  final _ReportFilterSet _self;
  final $Res Function(_ReportFilterSet) _then;

/// Create a copy of ReportFilterSet
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? periodBy = null,Object? status = null,Object? type = null,Object? category = null,Object? ci = null,Object? assignee = freezed,Object? approver = freezed,Object? approvedBy = freezed,Object? q = freezed,}) {
  return _then(_ReportFilterSet(
periodBy: null == periodBy ? _self.periodBy : periodBy // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self._status : status // ignore: cast_nullable_to_non_nullable
as List<String>,type: null == type ? _self._type : type // ignore: cast_nullable_to_non_nullable
as List<String>,category: null == category ? _self._category : category // ignore: cast_nullable_to_non_nullable
as List<String>,ci: null == ci ? _self._ci : ci // ignore: cast_nullable_to_non_nullable
as List<String>,assignee: freezed == assignee ? _self.assignee : assignee // ignore: cast_nullable_to_non_nullable
as String?,approver: freezed == approver ? _self.approver : approver // ignore: cast_nullable_to_non_nullable
as String?,approvedBy: freezed == approvedBy ? _self.approvedBy : approvedBy // ignore: cast_nullable_to_non_nullable
as String?,q: freezed == q ? _self.q : q // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}


/// @nodoc
mixin _$ReportRequest {

 String get kind;/// null with `kind = register` = all companies where the user is an
/// auditor.
 String? get companyId; String? get changeId; DateTime? get periodFrom; DateTime? get periodTo; ReportFilterSet get filters; bool get includeAuditTrail;
/// Create a copy of ReportRequest
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ReportRequestCopyWith<ReportRequest> get copyWith => _$ReportRequestCopyWithImpl<ReportRequest>(this as ReportRequest, _$identity);

  /// Serializes this ReportRequest to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  final _this = this as ReportRequest;
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ReportRequest&&(identical(other.kind, _this.kind) || other.kind == _this.kind)&&(identical(other.companyId, _this.companyId) || other.companyId == _this.companyId)&&(identical(other.changeId, _this.changeId) || other.changeId == _this.changeId)&&(identical(other.periodFrom, _this.periodFrom) || other.periodFrom == _this.periodFrom)&&(identical(other.periodTo, _this.periodTo) || other.periodTo == _this.periodTo)&&(identical(other.filters, _this.filters) || other.filters == _this.filters)&&(identical(other.includeAuditTrail, _this.includeAuditTrail) || other.includeAuditTrail == _this.includeAuditTrail));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
  final _this = this as ReportRequest;
  return Object.hash(runtimeType,_this.kind,_this.companyId,_this.changeId,_this.periodFrom,_this.periodTo,_this.filters,_this.includeAuditTrail);
}

@override
String toString() {
  final _this = this as ReportRequest;
  return 'ReportRequest(kind: ${_this.kind}, companyId: ${_this.companyId}, changeId: ${_this.changeId}, periodFrom: ${_this.periodFrom}, periodTo: ${_this.periodTo}, filters: ${_this.filters}, includeAuditTrail: ${_this.includeAuditTrail})';
}


}

/// @nodoc
abstract mixin class $ReportRequestCopyWith<$Res>  {
  factory $ReportRequestCopyWith(ReportRequest value, $Res Function(ReportRequest) _then) = _$ReportRequestCopyWithImpl;
@useResult
$Res call({
 String kind, String? companyId, String? changeId, DateTime? periodFrom, DateTime? periodTo, ReportFilterSet filters, bool includeAuditTrail
});


$ReportFilterSetCopyWith<$Res> get filters;

}
/// @nodoc
class _$ReportRequestCopyWithImpl<$Res>
    implements $ReportRequestCopyWith<$Res> {
  _$ReportRequestCopyWithImpl(this._self, this._then);

  final ReportRequest _self;
  final $Res Function(ReportRequest) _then;

/// Create a copy of ReportRequest
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? kind = null,Object? companyId = freezed,Object? changeId = freezed,Object? periodFrom = freezed,Object? periodTo = freezed,Object? filters = null,Object? includeAuditTrail = null,}) {
  return _then(ReportRequest(
kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as String,companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,changeId: freezed == changeId ? _self.changeId : changeId // ignore: cast_nullable_to_non_nullable
as String?,periodFrom: freezed == periodFrom ? _self.periodFrom : periodFrom // ignore: cast_nullable_to_non_nullable
as DateTime?,periodTo: freezed == periodTo ? _self.periodTo : periodTo // ignore: cast_nullable_to_non_nullable
as DateTime?,filters: null == filters ? _self.filters : filters // ignore: cast_nullable_to_non_nullable
as ReportFilterSet,includeAuditTrail: null == includeAuditTrail ? _self.includeAuditTrail : includeAuditTrail // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of ReportRequest
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$ReportFilterSetCopyWith<$Res> get filters {
  
  return $ReportFilterSetCopyWith<$Res>(_self.filters, (value) {
    return _then(_self.copyWith(filters: value));
  });
}
}


/// Adds pattern-matching-related methods to [ReportRequest].
extension ReportRequestPatterns on ReportRequest {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ReportRequest value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ReportRequest() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ReportRequest value)  $default,){
final _that = this;
switch (_that) {
case _ReportRequest():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ReportRequest value)?  $default,){
final _that = this;
switch (_that) {
case _ReportRequest() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String kind,  String? companyId,  String? changeId,  DateTime? periodFrom,  DateTime? periodTo,  ReportFilterSet filters,  bool includeAuditTrail)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ReportRequest() when $default != null:
return $default(_that.kind,_that.companyId,_that.changeId,_that.periodFrom,_that.periodTo,_that.filters,_that.includeAuditTrail);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String kind,  String? companyId,  String? changeId,  DateTime? periodFrom,  DateTime? periodTo,  ReportFilterSet filters,  bool includeAuditTrail)  $default,) {final _that = this;
switch (_that) {
case _ReportRequest():
return $default(_that.kind,_that.companyId,_that.changeId,_that.periodFrom,_that.periodTo,_that.filters,_that.includeAuditTrail);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String kind,  String? companyId,  String? changeId,  DateTime? periodFrom,  DateTime? periodTo,  ReportFilterSet filters,  bool includeAuditTrail)?  $default,) {final _that = this;
switch (_that) {
case _ReportRequest() when $default != null:
return $default(_that.kind,_that.companyId,_that.changeId,_that.periodFrom,_that.periodTo,_that.filters,_that.includeAuditTrail);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _ReportRequest implements ReportRequest {
  const _ReportRequest({required this.kind, this.companyId, this.changeId, this.periodFrom, this.periodTo, this.filters = const ReportFilterSet(), this.includeAuditTrail = false});
  factory _ReportRequest.fromJson(Map<String, dynamic> json) => _$ReportRequestFromJson(json);

@override final  String kind;
/// null with `kind = register` = all companies where the user is an
/// auditor.
@override final  String? companyId;
@override final  String? changeId;
@override final  DateTime? periodFrom;
@override final  DateTime? periodTo;
@override@JsonKey() final  ReportFilterSet filters;
@override@JsonKey() final  bool includeAuditTrail;

/// Create a copy of ReportRequest
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ReportRequestCopyWith<_ReportRequest> get copyWith => __$ReportRequestCopyWithImpl<_ReportRequest>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$ReportRequestToJson(this, );
}

@override
bool operator ==(Object other) {
    return identical(this, other) || (other.runtimeType == runtimeType&&other is _ReportRequest&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.companyId, companyId) || other.companyId == companyId)&&(identical(other.changeId, changeId) || other.changeId == changeId)&&(identical(other.periodFrom, periodFrom) || other.periodFrom == periodFrom)&&(identical(other.periodTo, periodTo) || other.periodTo == periodTo)&&(identical(other.filters, filters) || other.filters == filters)&&(identical(other.includeAuditTrail, includeAuditTrail) || other.includeAuditTrail == includeAuditTrail));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode {
    return Object.hash(runtimeType,kind,companyId,changeId,periodFrom,periodTo,filters,includeAuditTrail);
}

@override
String toString() {
    return 'ReportRequest(kind: $kind, companyId: $companyId, changeId: $changeId, periodFrom: $periodFrom, periodTo: $periodTo, filters: $filters, includeAuditTrail: $includeAuditTrail)';
}


}

/// @nodoc
abstract mixin class _$ReportRequestCopyWith<$Res> implements $ReportRequestCopyWith<$Res> {
  factory _$ReportRequestCopyWith(_ReportRequest value, $Res Function(_ReportRequest) _then) = __$ReportRequestCopyWithImpl;
@override @useResult
$Res call({
 String kind, String? companyId, String? changeId, DateTime? periodFrom, DateTime? periodTo, ReportFilterSet filters, bool includeAuditTrail
});


@override $ReportFilterSetCopyWith<$Res> get filters;

}
/// @nodoc
class __$ReportRequestCopyWithImpl<$Res>
    implements _$ReportRequestCopyWith<$Res> {
  __$ReportRequestCopyWithImpl(this._self, this._then);

  final _ReportRequest _self;
  final $Res Function(_ReportRequest) _then;

/// Create a copy of ReportRequest
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? kind = null,Object? companyId = freezed,Object? changeId = freezed,Object? periodFrom = freezed,Object? periodTo = freezed,Object? filters = null,Object? includeAuditTrail = null,}) {
  return _then(_ReportRequest(
kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as String,companyId: freezed == companyId ? _self.companyId : companyId // ignore: cast_nullable_to_non_nullable
as String?,changeId: freezed == changeId ? _self.changeId : changeId // ignore: cast_nullable_to_non_nullable
as String?,periodFrom: freezed == periodFrom ? _self.periodFrom : periodFrom // ignore: cast_nullable_to_non_nullable
as DateTime?,periodTo: freezed == periodTo ? _self.periodTo : periodTo // ignore: cast_nullable_to_non_nullable
as DateTime?,filters: null == filters ? _self.filters : filters // ignore: cast_nullable_to_non_nullable
as ReportFilterSet,includeAuditTrail: null == includeAuditTrail ? _self.includeAuditTrail : includeAuditTrail // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of ReportRequest
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$ReportFilterSetCopyWith<$Res> get filters {
  
  return $ReportFilterSetCopyWith<$Res>(_self.filters, (value) {
    return _then(_self.copyWith(filters: value));
  });
}
}

// dart format on
