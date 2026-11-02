import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

/// Error de red (sin conexión, tiempo agotado). Los datos locales no se tocan.
class NetworkException implements Exception {
  NetworkException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Respuesta de error del servidor.
class ApiException implements Exception {
  ApiException(this.message, {this.status});
  final String message;
  final int? status;
  bool get unauthorized => status == 401 || status == 403;
  @override
  String toString() => message;
}

abstract class SyncApi {
  Future<Map<String, dynamic>> push(Map<String, Object?> payload);
  Future<Map<String, dynamic>> pull({
    required int cursorVacas,
    required int cursorMediciones,
    required int cursorConfirmaciones,
    int limit,
  });
  Future<Map<String, dynamic>> manifest();
  Future<Uint8List> downloadLite();

  /// Libera recursos (un cliente nuevo se crea en cada sincronización).
  void close();
}

class HttpSyncApi implements SyncApi {
  HttpSyncApi({
    required String baseUrl,
    required this.token,
    http.Client? client,
    this.timeout = const Duration(seconds: 20),
  })  : baseUrl = baseUrl.replaceAll(RegExp(r'/+$'), ''),
        _client = client ?? http.Client();

  final String baseUrl;
  final String token;
  final Duration timeout;
  final http.Client _client;

  Map<String, String> get _headers => {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      };

  Future<http.Response> _send(Future<http.Response> Function() request) async {
    try {
      final response = await request().timeout(timeout);
      if (response.statusCode >= 400) {
        var detail = 'Error del servidor (${response.statusCode})';
        try {
          final body = jsonDecode(utf8.decode(response.bodyBytes));
          if (body is Map && body['detail'] is String) detail = body['detail'] as String;
        } catch (_) {}
        throw ApiException(detail, status: response.statusCode);
      }
      return response;
    } on TimeoutException {
      throw NetworkException('Tiempo de espera agotado');
    } on SocketException catch (e) {
      throw NetworkException('Sin conexión: ${e.message}');
    } on http.ClientException catch (e) {
      throw NetworkException('Sin conexión: ${e.message}');
    }
  }

  Map<String, dynamic> _json(http.Response r) =>
      jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;

  @override
  Future<Map<String, dynamic>> push(Map<String, Object?> payload) async => _json(await _send(
      () => _client.post(Uri.parse('$baseUrl/v1/sync/push'),
          headers: _headers, body: jsonEncode(payload))));

  @override
  Future<Map<String, dynamic>> pull({
    required int cursorVacas,
    required int cursorMediciones,
    required int cursorConfirmaciones,
    int limit = 500,
  }) async {
    final uri = Uri.parse('$baseUrl/v1/sync/pull').replace(queryParameters: {
      'cursor_vacas': '$cursorVacas',
      'cursor_mediciones': '$cursorMediciones',
      'cursor_confirmaciones': '$cursorConfirmaciones',
      'limit': '$limit',
    });
    return _json(await _send(() => _client.get(uri, headers: _headers)));
  }

  @override
  Future<Map<String, dynamic>> manifest() async => _json(
      await _send(() => _client.get(Uri.parse('$baseUrl/v1/model/manifest'), headers: _headers)));

  @override
  void close() => _client.close();

  @override
  Future<Uint8List> downloadLite() async => (await _send(
          () => _client.get(Uri.parse('$baseUrl/v1/model/lite'), headers: _headers)))
      .bodyBytes;
}
