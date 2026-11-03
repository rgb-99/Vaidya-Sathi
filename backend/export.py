"""FHIR-inspired JSON bundle (Patient, Encounter, Observation, MedicationRequest). It is NOT FHIR-compliant and
makes no ABDM claim; resource shapes are simplified. Each resource carries the audit trail for its fields."""

VITAL_NAMES = {'bp': 'Blood pressure', 'temp': 'Body temperature (F)', 'spo2': 'SpO2', 'pulse': 'Pulse',
               'resp_rate': 'Respiratory rate', 'sugar': 'Blood sugar'}


def _prov(record, *paths):
    return [{'field': p, **record.provenance[p].model_dump()} for p in paths if p in record.provenance]


def bundle(record, record_id):
    pid, eid = f'patient-{record_id}', f'encounter-{record_id}'
    patient = {'resourceType': 'Patient', 'id': pid, 'name': [{'text': record.patient.name}],
               'gender': record.patient.sex, 'extension': [{'url': 'age', 'valueString': record.patient.age}],
               'audit': _prov(record, 'patient.name', 'patient.age', 'patient.sex')}
    encounter = {'resourceType': 'Encounter', 'id': eid, 'status': 'finished', 'subject': {'reference': pid},
                 'reasonCode': [{'text': c} for c in record.chief_complaints],
                 'diagnosis': [{'text': record.diagnosis}] if record.diagnosis else [],
                 'audit': _prov(record, *[f'chief_complaints.{i}' for i in range(len(record.chief_complaints))], 'diagnosis')}
    entries = [patient, encounter]
    for key, label in VITAL_NAMES.items():
        value = getattr(record.vitals, key)
        if value:
            entries.append({'resourceType': 'Observation', 'id': f'obs-{key}-{record_id}', 'status': 'final',
                            'code': {'text': label}, 'valueString': value, 'subject': {'reference': pid},
                            'encounter': {'reference': eid}, 'audit': _prov(record, f'vitals.{key}')})
    for i, rx in enumerate(record.prescription):
        entries.append({'resourceType': 'MedicationRequest', 'id': f'rx-{i}-{record_id}', 'status': 'active', 'intent': 'order',
                        'medicationCodeableConcept': {'text': rx.drug}, 'subject': {'reference': pid},
                        'encounter': {'reference': eid}, 'authoredOn': record.signed_at,
                        'requester': {'display': record.signed_off_by},
                        'dosageInstruction': [{'text': ' '.join(x for x in (rx.dose, rx.frequency, rx.timing, rx.duration) if x)}],
                        'audit': _prov(record, *[f'prescription.{i}.{f}' for f in ('drug', 'dose', 'frequency', 'timing', 'duration')])})
    return {'resourceType': 'Bundle', 'type': 'collection',
            'meta': {'tag': [{'display': 'FHIR-inspired export. Not FHIR-compliant. No ABDM compliance claim.'}]},
            'signed_off_by': record.signed_off_by, 'signed_at': record.signed_at,
            'entry': [{'resource': r} for r in entries]}
