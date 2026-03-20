-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Nov 01, 2025 at 08:06 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.1.25

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `goldapidb`
--

-- --------------------------------------------------------

--
-- Table structure for table `activity_logs`
--

CREATE TABLE `activity_logs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED DEFAULT NULL,
  `action` varchar(255) NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `activity_logs`
--

INSERT INTO `activity_logs` (`id`, `user_id`, `action`, `ip_address`, `created_at`) VALUES
(1, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 17:18:53'),
(2, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 17:27:37'),
(3, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 17:27:43'),
(4, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 17:28:04'),
(5, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:02:55'),
(6, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:03:02'),
(7, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:07:28'),
(8, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:25:36'),
(9, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:30:18'),
(10, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:41:53'),
(11, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:42:57'),
(12, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:43:10'),
(13, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:43:52'),
(14, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 18:43:57'),
(15, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 19:00:32'),
(16, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 19:04:16'),
(17, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 19:04:44'),
(18, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-21 19:06:46'),
(19, 1, 'admin_updated_user (ID: 3)', '::1', '2025-10-22 05:56:21'),
(20, 1, 'admin_updated_user (ID: 3)', '::1', '2025-10-22 05:56:26'),
(21, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-22 05:56:47'),
(22, 1, 'admin_updated_user (ID: 4)', '::1', '2025-10-22 06:51:51'),
(23, 1, 'admin_updated_user (ID: 4)', '::1', '2025-10-22 06:52:41'),
(24, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-22 07:37:24'),
(25, 1, 'admin_updated_user (ID: 4)', '::1', '2025-10-22 10:11:21'),
(26, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-22 15:44:16'),
(27, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-22 15:44:34'),
(28, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-22 16:21:49'),
(29, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-22 16:22:09'),
(30, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-22 16:22:17'),
(31, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-23 06:18:10'),
(32, 1, 'admin_updated_user (ID: 2)', '::1', '2025-10-23 06:18:45'),
(33, 1, 'admin_updated_user (ID: 4)', '::1', '2025-10-23 13:38:23');

-- --------------------------------------------------------

--
-- Table structure for table `api_request_logs`
--

CREATE TABLE `api_request_logs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED DEFAULT NULL,
  `route` varchar(255) NOT NULL,
  `method` varchar(10) NOT NULL,
  `status_code` int(10) UNSIGNED NOT NULL,
  `latency_ms` int(10) UNSIGNED DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` varchar(512) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `auth_logs`
--

CREATE TABLE `auth_logs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `event` enum('login_success','login_failed','logout') NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` varchar(512) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `calculation_history`
--

CREATE TABLE `calculation_history` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED NOT NULL,
  `weight` decimal(10,3) NOT NULL,
  `unit` varchar(20) NOT NULL,
  `result_gram` decimal(10,3) DEFAULT NULL,
  `result_baht` decimal(10,3) DEFAULT NULL,
  `bar_buy_value` decimal(12,2) DEFAULT NULL,
  `bar_sell_value` decimal(12,2) DEFAULT NULL,
  `jewelry_buy_value` decimal(12,2) DEFAULT NULL,
  `jewelry_sell_value` decimal(12,2) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `cron_job_runs`
--

CREATE TABLE `cron_job_runs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `job_name` varchar(100) NOT NULL,
  `started_at` datetime NOT NULL,
  `finished_at` datetime DEFAULT NULL,
  `success` tinyint(1) NOT NULL DEFAULT 1,
  `details` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `email_logs`
--

CREATE TABLE `email_logs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED DEFAULT NULL,
  `recipient_email` varchar(255) NOT NULL,
  `subject` varchar(255) DEFAULT NULL,
  `status` enum('sent','failed') NOT NULL,
  `error_message` text DEFAULT NULL,
  `sent_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `email_verifications`
--

CREATE TABLE `email_verifications` (
  `id` int(10) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED NOT NULL,
  `token` varchar(255) NOT NULL,
  `status` enum('pending','verified','expired') DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `verified_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `price_alerts`
--

CREATE TABLE `price_alerts` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED NOT NULL,
  `target_price` decimal(10,2) NOT NULL,
  `alert_type` enum('above','below') NOT NULL,
  `gold_type` enum('bar','ornament','world') NOT NULL DEFAULT 'bar',
  `channel_email` tinyint(1) NOT NULL DEFAULT 0,
  `notify_email` varchar(255) DEFAULT NULL,
  `triggered` tinyint(1) NOT NULL DEFAULT 0,
  `triggered_at` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `price_cache`
--

CREATE TABLE `price_cache` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `date` date NOT NULL,
  `bar_buy` decimal(10,2) DEFAULT NULL,
  `bar_sell` decimal(10,2) DEFAULT NULL,
  `ornament_buy` decimal(10,2) DEFAULT NULL,
  `ornament_sell` decimal(10,2) DEFAULT NULL,
  `world_usd` decimal(10,2) DEFAULT NULL,
  `world_thb` decimal(10,2) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `rate_limits`
--

CREATE TABLE `rate_limits` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `identifier` varchar(255) NOT NULL,
  `action` varchar(50) NOT NULL,
  `ts_unix` int(10) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `rate_limits`
--

INSERT INTO `rate_limits` (`id`, `identifier`, `action`, `ts_unix`) VALUES
(4, '::1', 'auth_login', 1760905452),
(5, '::1', 'auth_login', 1760905462),
(6, '::1', 'auth_login', 1760905466),
(8, '::1', 'auth_login', 1760906286),
(9, '::1', 'auth_login', 1760906299),
(10, '::1', 'auth_login', 1760906311),
(11, '::1', 'auth_login', 1760906437),
(15, '::1', 'auth_login', 1760908199),
(18, '::1', 'auth_login', 1760912488),
(20, '::1', 'auth_login', 1760912860),
(22, '::1', 'auth_login', 1760913522),
(24, '::1', 'auth_login', 1760913552),
(26, '::1', 'auth_login', 1760913565),
(28, '::1', 'auth_login', 1760913671),
(30, '::1', 'auth_login', 1760914404),
(34, '::1', 'auth_login', 1761061082),
(36, '::1', 'auth_login', 1761061283),
(38, '::1', 'auth_login', 1761061406),
(41, '::1', 'auth_login', 1761062981),
(45, '::1', 'auth_login', 1761112745),
(47, '::1', 'auth_login', 1761115292),
(48, '::1', 'auth_login', 1761115821),
(49, '::1', 'auth_login', 1761115844),
(50, '::1', 'auth_login', 1761115844),
(53, '::1', 'auth_login', 1761115896),
(55, '::1', 'auth_login', 1761115924),
(57, '::1', 'auth_login', 1761115954),
(59, '::1', 'auth_login', 1761115975),
(61, '::1', 'auth_login', 1761118631),
(66, '::1', 'auth_login', 1761121602),
(67, '::1', 'auth_login', 1761121770),
(68, '::1', 'auth_login', 1761121770),
(69, '::1', 'auth_login', 1761121773),
(70, '::1', 'auth_login', 1761121773),
(72, '::1', 'auth_login', 1761122270),
(74, '::1', 'auth_login', 1761122296),
(76, '::1', 'auth_login', 1761122322),
(78, '::1', 'auth_login', 1761122377),
(79, '::1', 'auth_login', 1761122377),
(81, '::1', 'auth_login', 1761122434),
(82, '::1', 'auth_login', 1761122434),
(84, '::1', 'auth_login', 1761122559),
(85, '::1', 'auth_login', 1761122559),
(88, '::1', 'auth_login', 1761122814),
(90, '::1', 'auth_login', 1761127863),
(91, '::1', 'auth_login', 1761127863),
(93, '::1', 'auth_login', 1761127965),
(96, '::1', 'auth_login', 1761147561),
(98, '::1', 'auth_login', 1761147583),
(100, '::1', 'auth_login', 1761147624),
(102, '::1', 'auth_login', 1761147644),
(105, '::1', 'auth_login', 1761147817),
(106, '::1', 'auth_login', 1761147817),
(107, '::1', 'auth_login', 1761147833),
(108, '::1', 'auth_login', 1761147833),
(112, '::1', 'auth_login', 1761149474),
(115, '::1', 'auth_login', 1761149676),
(116, '::1', 'auth_login', 1761149694),
(117, '::1', 'auth_login', 1761149699),
(118, '::1', 'auth_login', 1761149812),
(119, '::1', 'auth_login', 1761149812),
(120, '::1', 'auth_login', 1761150024),
(121, '::1', 'auth_login', 1761150024),
(124, '::1', 'auth_login', 1761150074),
(126, '::1', 'auth_login', 1761150176),
(128, '::1', 'auth_login', 1761150576),
(130, '::1', 'auth_login', 1761150596),
(132, '::1', 'auth_login', 1761150702),
(133, '::1', 'auth_login', 1761150722),
(135, '::1', 'auth_login', 1761150741),
(137, '::1', 'auth_login', 1761150764),
(138, '::1', 'auth_login', 1761150780),
(139, '::1', 'auth_login', 1761150819),
(141, '::1', 'auth_login', 1761150832),
(143, '::1', 'auth_login', 1761150851),
(1, '::1', 'proxy_news', 1760903457),
(2, '::1', 'proxy_news', 1760904377),
(3, '::1', 'proxy_news', 1760905439),
(7, '::1', 'proxy_news', 1760906285),
(12, '::1', 'proxy_news', 1760907763),
(13, '::1', 'proxy_news', 1760908056),
(14, '::1', 'proxy_news', 1760908170),
(16, '::1', 'proxy_news', 1760911606),
(17, '::1', 'proxy_news', 1760912480),
(19, '::1', 'proxy_news', 1760912844),
(21, '::1', 'proxy_news', 1760913513),
(23, '::1', 'proxy_news', 1760913545),
(25, '::1', 'proxy_news', 1760913559),
(27, '::1', 'proxy_news', 1760913664),
(29, '::1', 'proxy_news', 1760914148),
(31, '::1', 'proxy_news', 1760914420),
(32, '::1', 'proxy_news', 1760988837),
(33, '::1', 'proxy_news', 1761060429),
(35, '::1', 'proxy_news', 1761061283),
(37, '::1', 'proxy_news', 1761061406),
(39, '::1', 'proxy_news', 1761061431),
(40, '::1', 'proxy_news', 1761061824),
(42, '::1', 'proxy_news', 1761066047),
(43, '::1', 'proxy_news', 1761112720),
(44, '::1', 'proxy_news', 1761112738),
(46, '::1', 'proxy_news', 1761115288),
(51, '::1', 'proxy_news', 1761115861),
(52, '::1', 'proxy_news', 1761115894),
(54, '::1', 'proxy_news', 1761115921),
(56, '::1', 'proxy_news', 1761115952),
(58, '::1', 'proxy_news', 1761115970),
(60, '::1', 'proxy_news', 1761118630),
(62, '::1', 'proxy_news', 1761119461),
(63, '::1', 'proxy_news', 1761120723),
(64, '::1', 'proxy_news', 1761120914),
(65, '::1', 'proxy_news', 1761121268),
(71, '::1', 'proxy_news', 1761122258),
(73, '::1', 'proxy_news', 1761122275),
(75, '::1', 'proxy_news', 1761122310),
(77, '::1', 'proxy_news', 1761122332),
(80, '::1', 'proxy_news', 1761122411),
(83, '::1', 'proxy_news', 1761122450),
(86, '::1', 'proxy_news', 1761122565),
(87, '::1', 'proxy_news', 1761122807),
(89, '::1', 'proxy_news', 1761127836),
(92, '::1', 'proxy_news', 1761127962),
(94, '::1', 'proxy_news', 1761130096),
(95, '::1', 'proxy_news', 1761147511),
(97, '::1', 'proxy_news', 1761147568),
(99, '::1', 'proxy_news', 1761147600),
(101, '::1', 'proxy_news', 1761147628),
(103, '::1', 'proxy_news', 1761147715),
(104, '::1', 'proxy_news', 1761147754),
(109, '::1', 'proxy_news', 1761147883),
(110, '::1', 'proxy_news', 1761149452),
(111, '::1', 'proxy_news', 1761149461),
(113, '::1', 'proxy_news', 1761149478),
(114, '::1', 'proxy_news', 1761149670),
(122, '::1', 'proxy_news', 1761150036),
(123, '::1', 'proxy_news', 1761150057),
(125, '::1', 'proxy_news', 1761150152),
(127, '::1', 'proxy_news', 1761150567),
(129, '::1', 'proxy_news', 1761150582),
(131, '::1', 'proxy_news', 1761150612),
(134, '::1', 'proxy_news', 1761150730),
(136, '::1', 'proxy_news', 1761150755),
(140, '::1', 'proxy_news', 1761150830),
(142, '::1', 'proxy_news', 1761150842),
(144, '::1', 'proxy_news', 1761150880),
(145, '::1', 'proxy_news', 1761151252),
(146, '::1', 'proxy_news', 1761151319),
(147, '::1', 'proxy_news', 1761151329),
(148, '::1', 'proxy_news', 1761151739),
(149, '::1', 'proxy_news', 1761151899),
(150, '::1', 'proxy_news', 1761152821),
(151, '::1', 'proxy_news', 1761152942),
(152, '::1', 'proxy_news', 1761152961),
(153, '::1', 'proxy_news', 1761152994),
(154, '::1', 'proxy_news', 1761153580),
(155, '::1', 'proxy_news', 1761153587),
(156, '::1', 'proxy_news', 1761153986),
(157, '::1', 'proxy_news', 1761154001),
(158, '::1', 'proxy_news', 1761154059),
(159, '::1', 'proxy_news', 1761200257),
(160, '::1', 'proxy_news', 1761200392),
(161, '::1', 'proxy_news', 1761200404),
(162, '::1', 'proxy_news', 1761200509),
(163, '::1', 'proxy_news', 1761200550),
(164, '::1', 'proxy_news', 1761200723),
(165, '::1', 'proxy_news', 1761200732),
(166, '::1', 'proxy_news', 1761200768),
(167, '::1', 'proxy_news', 1761213579),
(168, '::1', 'proxy_news', 1761215431),
(169, '::1', 'proxy_news', 1761215657),
(170, '::1', 'proxy_news', 1761215870),
(171, '::1', 'proxy_news', 1761216168),
(172, '::1', 'proxy_news', 1761216289),
(173, '::1', 'proxy_news', 1761216882),
(174, '::1', 'proxy_news', 1761216956),
(175, '::1', 'proxy_news', 1761217490),
(176, '::1', 'proxy_news', 1761217593),
(177, '::1', 'proxy_news', 1761217600),
(178, '::1', 'proxy_news', 1761221982),
(179, '::1', 'proxy_news', 1761224800),
(180, '::1', 'proxy_news', 1761226650),
(181, '::1', 'proxy_news', 1761226672),
(182, '::1', 'proxy_news', 1761227340),
(183, '::1', 'proxy_news', 1761227342),
(184, '::1', 'proxy_news', 1761227407),
(185, '::1', 'proxy_news', 1761227432),
(186, '::1', 'proxy_news', 1761231032),
(187, '::1', 'proxy_news', 1761233727),
(188, '::1', 'proxy_news', 1761233880),
(189, '::1', 'proxy_news', 1761234247),
(190, '::1', 'proxy_news', 1761234321),
(191, '::1', 'proxy_news', 1761234399),
(192, '::1', 'proxy_news', 1761234459),
(193, '::1', 'proxy_news', 1761234830),
(194, '::1', 'proxy_news', 1761237904),
(195, '::1', 'proxy_news', 1761238693),
(196, '::1', 'proxy_news', 1761238715),
(197, '::1', 'proxy_news', 1761238758),
(198, '::1', 'proxy_news', 1761239125),
(199, '::1', 'proxy_news', 1761240212),
(200, '::1', 'proxy_news', 1761240429),
(201, '::1', 'proxy_news', 1761243055),
(202, '::1', 'proxy_news', 1761244029),
(203, '::1', 'proxy_news', 1761247631),
(204, '::1', 'proxy_news', 1761247949),
(205, '::1', 'proxy_news', 1761248070);

-- --------------------------------------------------------

--
-- Table structure for table `sessions`
--

CREATE TABLE `sessions` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` int(10) UNSIGNED NOT NULL,
  `token` char(64) NOT NULL,
  `expires_at` datetime NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `sessions`
--

INSERT INTO `sessions` (`id`, `user_id`, `token`, `expires_at`, `created_at`, `ip_address`, `user_agent`) VALUES
(1, 1, '18728d0762025a0a275eec95b923d0533a925d4f4f9b8d6449b05f36ea674b53', '2025-10-27 00:21:28', '2025-10-19 22:21:28', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(2, 1, '2a8019704d1e1be563ddfda7a8dabb5db9d8e871f84f1fcf4f025ff9774fac24', '2025-10-27 00:27:40', '2025-10-19 22:27:40', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(4, 1, 'ab41a31a7fe04221485f944c7dab3ae5bb2e37090aacecb454de66195f96b098', '2025-10-27 00:39:12', '2025-10-19 22:39:12', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(5, 1, '08d7262c4369f58fb0d9c28ac706dbbb01d68bdefcf12f0c0113472332a3c55b', '2025-10-27 00:39:25', '2025-10-19 22:39:25', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(13, 1, '7d9daec467641ced852ee2d5bb2d03b0b675199946eb192bc0e254a2ec4767c2', '2025-10-29 08:41:32', '2025-10-22 06:41:32', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(14, 4, 'b38f1024c1564ffd4cc8520cd164efc79b92df06e177fecf8b70bff4e4f2c52c', '2025-10-29 08:50:21', '2025-10-22 06:50:21', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(15, 1, '10e65eecf8e280f4a1c7ec3308b49158e51402d2ad2aecc76e85f86bf04ec7eb', '2025-10-29 08:50:44', '2025-10-22 06:50:44', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(20, 4, 'd260133fc1d00cf48443db35b5e3bcc91b0333767c1250856eeb2e660e66fcf8', '2025-10-29 08:52:55', '2025-10-22 06:52:55', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(21, 1, 'ebe32f1a51b869519a76a8a1b001bbb3147e60a335ce86f7e302b0601d42bf7d', '2025-10-29 09:37:11', '2025-10-22 07:37:11', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(22, 4, '2c10fb668e22fa25a8fe5aff1a2fac2cef3d41cb4ac82468495e36754f1c06f6', '2025-10-29 10:26:42', '2025-10-22 08:26:42', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(23, 4, 'cda6d0afd5fc79adc8e25cc8a99094e92cb5e9ec2ac00a5197f2dc890fc9e60a', '2025-10-29 10:29:30', '2025-10-22 08:29:30', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(24, 4, '5bc4f085417462db04eed824755a7f021718972354de5ac91527975d85a16255', '2025-10-29 10:29:30', '2025-10-22 08:29:30', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(25, 4, 'ef9e052da1e7641cef637df29b03ee6d8b3eada3f4012dd97ef8504e97e15e09', '2025-10-29 10:29:33', '2025-10-22 08:29:33', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(26, 4, '81a401e1165691b640e563779b8f3561d2674090bd79222c2893558f09a8f32a', '2025-10-29 10:29:33', '2025-10-22 08:29:33', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(27, 4, '16138f6568f2ca5baa26d63ef10a2d6a27cb1cd5b32217dd7be02c0b1a0e746e', '2025-10-29 10:37:50', '2025-10-22 08:37:50', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(28, 4, 'd6f0677d497e0d3ac2552515c8c68d677764370e299a799888849d3cc3d78b07', '2025-10-29 10:38:16', '2025-10-22 08:38:16', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(29, 4, '6e9329d8a2f3f534370d8e71eb0aece4ce9132b86bae46ae43c583ebea26fee1', '2025-10-29 10:38:42', '2025-10-22 08:38:42', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(30, 1, '6cec9473d0d82b7b3f0d5c73546364e990beb63cf6e4706cb94194c5f5561b3c', '2025-10-29 10:39:37', '2025-10-22 08:39:37', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(32, 1, 'a431555e91fb991035da5a353810d9a4d0401540dbbdf0dcc4ae896968adcf9c', '2025-10-29 10:40:34', '2025-10-22 08:40:34', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(34, 4, 'a5c7aa2c82c20853bcbff75d8a4bcfbc6ce568beeea2535626c4dd05d448140d', '2025-10-29 10:42:39', '2025-10-22 08:42:39', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(35, 4, '93869c0b23f7965f4663044f50b64112e200b5377858b335fe1b60438277c7a8', '2025-10-29 10:42:39', '2025-10-22 08:42:39', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(36, 1, '0a064842b978870e422c6bbc8ab6a73caeff11a1670f9c44dc06acd96ff8679b', '2025-10-29 10:46:54', '2025-10-22 08:46:54', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(38, 1, 'a746a1de43c3d33a1d6f9175425b38d2789622664f71681892619af1a997c23b', '2025-10-29 12:11:03', '2025-10-22 10:11:03', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(39, 1, '5d852b8441a85125d44f2739db608d4dd2d418b860ccd7f45cc4d8cf919a84c3', '2025-10-29 12:12:45', '2025-10-22 10:12:45', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(40, 4, '93dc678c67245bcb7ca8b801c33371f089b55f4742916869ed0a88d33768a92d', '2025-10-29 17:39:21', '2025-10-22 15:39:21', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(41, 4, 'b5448ce90650774b867ea8f4dad2192a3b675ae28d6b8feda1a4aeea07e0f763', '2025-10-29 17:39:43', '2025-10-22 15:39:43', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(42, 4, '34ebb3ece2e32b501bc486320c3b273155451a92a763f8c2134b59dc57e16964', '2025-10-29 17:40:24', '2025-10-22 15:40:24', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(43, 4, '0743b444c873d0f2c9e5b3c6bb6c9f3df83494194d2ddc543ab1b0a0881c631a', '2025-10-29 17:40:44', '2025-10-22 15:40:44', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(44, 1, 'd220266cfd54c5a8910780860847b26fbd135acbd96eec3c86486cc2e1dee232', '2025-10-29 17:43:53', '2025-10-22 15:43:53', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(46, 4, '43e51a2a6a87540074820eed8fa96068a7505f9102263d55c11f8eb3ffeb194a', '2025-10-29 18:11:14', '2025-10-22 16:11:14', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(47, 1, '4dbd9005def96b5d84bfefc6754ccdc8746fab35dafb4f4bae894ec50282d031', '2025-10-29 18:20:24', '2025-10-22 16:20:24', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(51, 4, '517733167e15ca4afe65676ad95512595122050b4cd6c8b9e82e9681be6c088c', '2025-10-29 18:29:36', '2025-10-22 16:29:36', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(52, 4, 'fe0cc828e9a77c0a9dad0875341c67c01cba5b7183ef15e8b992144af43251c7', '2025-10-29 18:29:56', '2025-10-22 16:29:56', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(58, 1, '4396eac625bf4a1ee8359337ce5ef921096902b245098ea4eec19e1316ccf61e', '2025-10-29 18:42:23', '2025-10-22 16:42:23', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(60, 1, '38a6a28bd952cb8fd4ef3b01148c03557ef26c7e100517dd2c51b3e4966f02ce', '2025-10-29 18:52:33', '2025-10-22 16:52:33', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(61, 1, '22f29f96511593ff3a0f6fe1d349881d45a580224bc7abcd56342e149f7b22ad', '2025-10-29 18:52:33', '2025-10-22 16:52:33', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(63, 4, '67047b75cc3dba8ba63b0521090bac38e3eeefe8246e5d1f9e7abe74af1725a5', '2025-10-29 19:09:16', '2025-10-22 17:09:16', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(64, 4, 'cdf88839c516d4ae91fa2f2128ea235c6145ada4a9eab6f5e41ff7a553da7a8f', '2025-10-29 19:09:41', '2025-10-22 17:09:41', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(67, 4, '29cdd202ef932273ca4287824dcfb57b70280bc78f8fb2c5d5c95cb428697463', '2025-10-29 19:26:36', '2025-10-22 17:26:36', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(68, 4, 'b6b50500e6b39e18904080a1ca0199d0962eba437f1a5f451147ba26d2fac4f2', '2025-10-29 19:27:08', '2025-10-22 17:27:08', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(69, 4, 'e8afc429ccfe6bb48d287bb97d8e694319abecd653c92eb9cbb7d23426d33d00', '2025-10-29 19:34:54', '2025-10-22 17:34:54', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(70, 4, '8c248dc63733c8443775a78171b3897a871f260e8a128092b22640c076f74864', '2025-10-29 19:34:54', '2025-10-22 17:34:54', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(72, 4, 'ea4daa6e1112105abbfcda555cda4a97dbc8d0f1f950c261559ea2c39c56be6b', '2025-10-30 08:20:00', '2025-10-23 06:20:00', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(74, 4, '0517f98689e75cfdb753d1fa058fdff50ea5643d71dc72e38cb964f865ca02f1', '2025-10-30 08:25:48', '2025-10-23 06:25:48', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(78, 1, '6a0aec9c8ca14aa16ca751f7c933813835361d84e2131c9e3997ab7a0df76b30', '2025-10-30 12:45:33', '2025-10-23 10:45:33', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(82, 4, 'e9e71f9effccbecfa0df6934290d226542d134b78145bbf06bc56f6cd093ab3b', '2025-10-30 13:06:38', '2025-10-23 11:06:38', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(84, 4, 'ad09ad1c4cff25e7551bb0366fcd30747452e0007ee388d862f178405eff3b1e', '2025-10-30 15:49:20', '2025-10-23 13:49:20', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(85, 4, '57d07ebbe6d5595b95fe8c9b88745f88192b1650348f86c4835f2908d418c74d', '2025-10-30 15:50:27', '2025-10-23 13:50:27', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(86, 1, '43c066637f15038114cd656e176c955721195af22f538019988ee60f7a11d947', '2025-10-30 22:11:15', '2025-10-23 20:11:15', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(87, 1, '7ace4d73fb2f63bf2c144880187239293ffc0af64e97506eceea4452b19ff5ee', '2025-10-30 22:47:10', '2025-10-23 20:47:10', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(88, 4, '2a009bed2803797fe3a69e229bcc1baa189c7d3473453eaa865224d63914f3fd', '2025-10-30 23:02:43', '2025-10-23 21:02:43', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(89, 1, 'd9aed8feca54f1810565fe69595cfd81ef7b8a6544cc4972eb35c79cfc4f8989', '2025-10-31 22:23:19', '2025-10-24 20:23:19', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(90, 1, 'd84163347a9c71d5ca58ee03c854e7d1375cccbe3fcf92c90347d084c75c0a68', '2025-10-31 23:33:00', '2025-10-24 21:33:00', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(91, 1, 'f122fa474cb507a200bdc46a17065f74f6a29023d22fba1c1afd1c49732184c7', '2025-10-31 23:33:00', '2025-10-24 21:33:00', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(92, 4, 'e0e08f47fd1e413870d90bce6a03927dcdfbb304b8a8b4433b5032c25d22ed06', '2025-10-31 23:34:08', '2025-10-24 21:34:08', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(93, 1, '9e0f6b193d3628852fb4d7d2798482be86d1217123d453ebe68c5650b458ed49', '2025-10-31 23:36:40', '2025-10-24 21:36:40', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(94, 4, '82178fa10e4e6057d94b855ab803e1930461bd73955fc88f85cf666be18597ba', '2025-10-31 23:41:34', '2025-10-24 21:41:34', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(95, 1, 'c3d5ce9489fd12bd8bf140559ce17f07c3442ce723582c871545eec530243366', '2025-10-31 23:47:12', '2025-10-24 21:47:12', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(96, 4, '40fd082f23b651d537373b09fd6606dbb76976b65672eda0e881d893ad0c07a6', '2025-11-01 14:32:51', '2025-10-25 12:32:51', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(97, 4, '1561c393336aaea0f3bb42e533145a7163353c436397f2b4cf9e0f1009d76016', '2025-11-01 14:32:51', '2025-10-25 12:32:51', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(101, 1, '12c3492177c8f9c55ad9736fe3e8f3db752b2b37e1334cb03e93e0251791503b', '2025-11-01 15:33:57', '2025-10-25 13:33:57', '::1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'),
(103, 1, '7bf74939cf50e944fa00ccf5d090348c39a60de2595aaed09dd3e8782b1d8403', '2025-11-01 15:43:33', '2025-10-25 14:43:33', NULL, NULL),
(104, 1, 'ff371f03d1fc9ccc1546afa4d762bed1a64f75d82f4e903187df21462fc0e8c2', '2025-11-01 15:43:33', '2025-10-25 14:43:33', NULL, NULL),
(105, 1, '44bd318c2b93a72d91a4728ca426269d39003e8651c4351534df77309526512c', '2025-11-01 15:44:05', '2025-10-25 14:44:05', NULL, NULL),
(106, 1, 'e70e821a7e0ef15528a25e7b843c1aa1c70863a5e55d037161d47307d72d8a04', '2025-11-01 15:44:05', '2025-10-25 14:44:05', NULL, NULL),
(108, 4, '6306853578f57657fd95af6e8ae76318d7366114f060a2303fa6a4d8af111ed2', '2025-11-01 16:31:53', '2025-10-25 15:31:53', NULL, NULL),
(109, 1, '193d9534d9a00f337c946db4e87e1cca76077403db41ec4c75c1747c373e7d8c', '2025-11-01 16:32:52', '2025-10-25 15:32:52', NULL, NULL),
(111, 5, '6fb62b4ff990023fea51231e83765e678574bd6ccd1c958e61eaa9278c0c5279', '2025-11-01 16:36:27', '2025-10-25 15:36:27', NULL, NULL),
(112, 5, '2b0c46754c9130643289b4e70739ea00ad05ac37a0bde4687098c32413090c84', '2025-11-01 16:43:07', '2025-10-25 15:43:07', NULL, NULL),
(113, 5, '047e1e93c3edd4dcaad88a6fd90a3d1b49ef77f9b1d263f8918a0bc3323af4ed', '2025-11-01 16:47:48', '2025-10-25 15:47:48', NULL, NULL),
(114, 5, '805e49d46fec0d043b639cbdd26e25241f8a4dce5687166bf4d4e0d766db1e53', '2025-11-01 16:55:16', '2025-10-25 15:55:16', NULL, NULL),
(119, 4, 'a13ba721d379626bf42df998d77ade9e923177f58aa714fad50eaf619263809e', '2025-11-02 07:24:27', '2025-10-26 06:24:27', NULL, NULL),
(120, 1, '56b512ad3c0ee2121fe267245b1b4b2f9836eb51f1dd8f9622aabd477d6bbd85', '2025-11-02 07:24:59', '2025-10-26 06:24:59', NULL, NULL),
(122, 1, '5bae3e445f244b33954685d16286bf68c43147554b2d1d46b825f3adb31eb64a', '2025-11-02 16:40:21', '2025-10-26 15:40:21', NULL, NULL),
(130, 6, '260f24d5dfd356e178a2463ce14226d69bf687000871b802d6343c486828484e', '2025-11-03 07:37:08', '2025-10-27 06:37:08', NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(10) UNSIGNED NOT NULL,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `is_verified` tinyint(1) NOT NULL DEFAULT 0,
  `role` enum('user','admin') NOT NULL DEFAULT 'user',
  `last_login` datetime DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `is_active` tinyint(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `email`, `password_hash`, `name`, `is_verified`, `role`, `last_login`, `created_at`, `updated_at`, `is_active`) VALUES
(1, 'admin@admin.com', '$2y$10$3X1MNBoqdiDKfd8fx/nm3uW6O3RlB7uAw1FjBlpwj3mh1l..KB3Eu', 'Administrator', 1, 'admin', NULL, '2025-10-19 16:37:14', '2025-10-19 21:12:42', 1),
(2, 'test_1760911037@example.com', '$2y$10$s7f5HLTxlm2oP7VNlDdLqeFhxvmPU7yMomP6u6Oq05jK48vt.9WNK', 'Test User 235717', 1, 'user', NULL, '2025-10-19 21:57:17', '2025-10-29 05:21:57', 1),
(3, 'test_1761060569@example.com', '$2y$10$juZ41lSVu0VTc7b0ED2PW.QV8/ElkCDa8FHk8sIM.eR7F2ok4OWXC', 'Test User 172929', 1, 'user', NULL, '2025-10-21 15:29:29', '2025-10-22 05:56:26', 1),
(4, 'a123@gmail.com', '$2y$10$eHnNlXs1Acjs.ZRpdF81WeLCIwdH5renPYTHW/55vqfufa1HXhFAm', 'a', 0, 'user', NULL, '2025-10-22 06:49:47', '2025-10-26 06:28:46', 1),
(5, 'ab123@gmail.com', '$2y$10$USiNqc4X75WMJ40Yn8Pc3.HveI6SqcTlZl2PoMPMUzZLt7nWNL1Ga', 'ab', 0, 'user', NULL, '2025-10-25 15:35:26', '2025-10-26 06:27:46', 1),
(6, 'abc123@gmail.com', '$2y$10$6g64xLEjLNy8V6ril.rNtuoyLXJqNoCwiXcfDNPN.kjEbqfnWM082', 'abcc', 0, 'user', NULL, '2025-10-26 15:44:36', '2025-10-29 06:23:44', 1);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `activity_logs`
--
ALTER TABLE `activity_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_activity_logs_user` (`user_id`);

--
-- Indexes for table `api_request_logs`
--
ALTER TABLE `api_request_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_api_logs_user` (`user_id`);

--
-- Indexes for table `auth_logs`
--
ALTER TABLE `auth_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_auth_user` (`user_id`);

--
-- Indexes for table `calculation_history`
--
ALTER TABLE `calculation_history`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_calc_user` (`user_id`);

--
-- Indexes for table `cron_job_runs`
--
ALTER TABLE `cron_job_runs`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `email_logs`
--
ALTER TABLE `email_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_email_user` (`user_id`);

--
-- Indexes for table `email_verifications`
--
ALTER TABLE `email_verifications`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_ev_user` (`user_id`);

--
-- Indexes for table `price_alerts`
--
ALTER TABLE `price_alerts`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_alert_active` (`user_id`,`target_price`,`alert_type`,`gold_type`,`triggered`),
  ADD KEY `idx_alerts_email` (`triggered`,`channel_email`);

--
-- Indexes for table `price_cache`
--
ALTER TABLE `price_cache`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_pricecache_date` (`date`);

--
-- Indexes for table `rate_limits`
--
ALTER TABLE `rate_limits`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_rate_lookup` (`identifier`,`action`,`ts_unix`);

--
-- Indexes for table `sessions`
--
ALTER TABLE `sessions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_sessions_token` (`token`),
  ADD KEY `fk_sessions_user` (`user_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_users_email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `activity_logs`
--
ALTER TABLE `activity_logs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=34;

--
-- AUTO_INCREMENT for table `api_request_logs`
--
ALTER TABLE `api_request_logs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `auth_logs`
--
ALTER TABLE `auth_logs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `calculation_history`
--
ALTER TABLE `calculation_history`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `cron_job_runs`
--
ALTER TABLE `cron_job_runs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `email_logs`
--
ALTER TABLE `email_logs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `email_verifications`
--
ALTER TABLE `email_verifications`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `price_alerts`
--
ALTER TABLE `price_alerts`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `price_cache`
--
ALTER TABLE `price_cache`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `rate_limits`
--
ALTER TABLE `rate_limits`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=206;

--
-- AUTO_INCREMENT for table `sessions`
--
ALTER TABLE `sessions`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=146;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `activity_logs`
--
ALTER TABLE `activity_logs`
  ADD CONSTRAINT `fk_activity_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `api_request_logs`
--
ALTER TABLE `api_request_logs`
  ADD CONSTRAINT `fk_api_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Constraints for table `auth_logs`
--
ALTER TABLE `auth_logs`
  ADD CONSTRAINT `fk_auth_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Constraints for table `calculation_history`
--
ALTER TABLE `calculation_history`
  ADD CONSTRAINT `fk_calc_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `email_logs`
--
ALTER TABLE `email_logs`
  ADD CONSTRAINT `fk_email_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Constraints for table `email_verifications`
--
ALTER TABLE `email_verifications`
  ADD CONSTRAINT `fk_ev_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `price_alerts`
--
ALTER TABLE `price_alerts`
  ADD CONSTRAINT `fk_alerts_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `sessions`
--
ALTER TABLE `sessions`
  ADD CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
