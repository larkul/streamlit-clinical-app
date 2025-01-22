-- Clear existing data
TRUNCATE TABLE disease_areas CASCADE;
ALTER SEQUENCE disease_areas_id_seq RESTART WITH 1;

-- Insert unique disease areas
INSERT INTO disease_areas (area_name, description) VALUES
('ONCOLOGY', 'Cancer and neoplastic diseases'),
('INFECTIOUS_DISEASE', 'Bacterial, viral, and fungal infections'),
('AUTOIMMUNE', 'Immune system disorders'),
('CARDIOVASCULAR', 'Heart and circulatory system diseases'),
('NEUROLOGY', 'Nervous system disorders'),
('RESPIRATORY', 'Respiratory system diseases'),
('ENDOCRINE', 'Hormonal and metabolic disorders'),
('GENITOURINARY', 'Genitourinary system diseases'),
('OPHTHALMOLOGY', 'Eye diseases'),
('CNS', 'Central nervous system diseases'),
('VACCINES', 'Vaccine development'),
('METABOLIC', 'Metabolic disorders'),
('RARE_DISEASES', 'Rare and orphan diseases'),
('OTHER', 'Other diseases not classified elsewhere');

-- Insert disease areas with ranking (1 = highest priority)
INSERT INTO disease_area_ranking (area_name, rank) VALUES
('ONCOLOGY', 1),
('CARDIOVASCULAR', 2),
('NEUROLOGY', 3),
('INFECTIOUS_DISEASE', 4),
('AUTOIMMUNE', 5),
('RESPIRATORY', 6),
('ENDOCRINE', 7),
('CNS', 8),
('GENITOURINARY', 9),
('METABOLIC', 10),
('RARE_DISEASES', 11),
('OPHTHALMOLOGY', 12),
('VACCINES', 13),
('OTHER', 14);

-- Insert hay probabilities with correct disease area IDs
INSERT INTO hay_probabilities 
(disease_area_id, phase_1_to_2, phase_2_to_3, phase_3_to_nda_bla, nda_bla_to_approval, loa_from_current_phase) VALUES
(1, 0.639, 0.283, 0.452, 0.817, 0.067),  -- ONCOLOGY
(2, 0.658, 0.459, 0.653, 0.849, 0.167),  -- INFECTIOUS_DISEASE
(3, 0.680, 0.340, 0.684, 0.803, 0.127),  -- AUTOIMMUNE
(4, 0.606, 0.263, 0.528, 0.845, 0.071),  -- CARDIOVASCULAR
(5, 0.624, 0.302, 0.606, 0.822, 0.094),  -- NEUROLOGY
(6, 0.667, 0.275, 0.633, 0.960, 0.111),  -- RESPIRATORY
(7, 0.583, 0.338, 0.674, 0.869, 0.116),  -- ENDOCRINE
(8, 0.642, 0.342, 0.572, 0.892, 0.108),  -- GENITOURINARY
(9, 0.645, 0.335, 0.585, 0.885, 0.105),  -- OPHTHALMOLOGY
(10, 0.624, 0.302, 0.606, 0.822, 0.094), -- CNS
(11, 0.658, 0.459, 0.653, 0.849, 0.167), -- VACCINES
(12, 0.583, 0.338, 0.674, 0.869, 0.116), -- METABOLIC
(13, 0.642, 0.342, 0.572, 0.892, 0.108), -- RARE_DISEASES
(14, 0.632, 0.337, 0.607, 0.855, 0.112); -- OTHER (Average of all values)
