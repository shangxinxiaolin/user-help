package com.shangui.userhelp.aftersales.mapper;

import com.shangui.userhelp.aftersales.domain.ReturnInfo;
import com.shangui.userhelp.aftersales.domain.WarrantyInfo;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.Random;

@Repository
public class MockAftersalesMapper implements AftersalesMapper {

    @Override
    public WarrantyInfo findWarranty(String orderId) {
        Random random = new Random(("warranty:" + orderId).hashCode());
        String status = random.nextBoolean() ? "在保" : "已过保";
        return new WarrantyInfo(orderId, status, LocalDate.of(2027, 7, 1) + "");
    }

    @Override
    public ReturnInfo findReturnStatus(String orderId) {
        String[] statuses = {"审核中", "退货中", "已退款", "无退货记录"};
        Random random = new Random(("return:" + orderId).hashCode());
        return new ReturnInfo(orderId, statuses[random.nextInt(statuses.length)], "2026-09-26 10:00");
    }
}
