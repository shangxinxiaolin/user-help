package com.shangui.userhelp.logistics.mapper;

import com.shangui.userhelp.logistics.domain.LogisticsInfo;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Random;

@Repository
public class MockLogisticsMapper implements LogisticsMapper {

    private static final String[] STATUSES = {"已揽件", "运输中", "派送中", "已签收"};
    private static final String[] CITIES = {"深圳", "广州", "杭州", "上海", "成都"};

    @Override
    public LogisticsInfo findByTrackingNo(String trackingNo) {
        if (trackingNo == null || trackingNo.isBlank()) {
            return null;
        }
        Random random = new Random(("logistics:" + trackingNo).hashCode());
        String status = STATUSES[random.nextInt(STATUSES.length)];
        String city = CITIES[random.nextInt(CITIES.length)];
        return new LogisticsInfo(trackingNo, status, city,
                List.of(city + "分拨中心 已发出", "内部状态码:" + status));
    }
}
